"""Reference-driven offline attributes with inspectable contribution sources.

AttrRef's 1/10000 percentages and power weights are captured client rules.
Cross-system stacking is a local model; no production server was recovered.
"""
from collections import defaultdict
import math
import json


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else 0
    except (TypeError, ValueError, OverflowError):
        return 0


def attributes(encoded):
    result = defaultdict(float)
    for entry in (encoded or "").split("#"):
        fields = entry.split("_")
        if len(fields) >= 2:
            result[int(fields[0])] += number(fields[1])
    return dict(result)


class OfflineStats:
    def __init__(self, store):
        self.store = store
        self.refs = {int(row["refId"]): row for row in store.table("AttrRef")}
        self.by_name = {row["attr"]: int(row["refId"]) for row in self.refs.values()}
        self.random = {int(row["refId"]): row for row in store.table("EquipRandomAttrRef")}
        self.skins = {(int(row["skinId"]), int(row["star"])): row for row in store.table("GeneralSkinStarRef")}
        self.pet_stages = {(int(row["refId"]), int(row["order"])): row for row in store.table("PetStageRef")}
        self.mount_stars = {(int(row["refId"]), int(row["star"])): row for row in store.table("MountStarRef")}
        self.mount_levels = {(int(row['refId']), int(row['level'])): row for row in store.table('MountLevelRef')}
        self.potential_by_general = defaultdict(list)
        for node_id, ref in store.potentials.items():
            self.potential_by_general[int(ref["generalId"])].append(node_id)

    def signature(self, state):
        # Only inputs to combat attributes belong here. Movement, inventory,
        # encounters and save timestamps must not invalidate the crew's math.
        keys = ('generals','potential','pets','mounts','companion','generalSkins',
                'activeFights','talent','treasures','gemBookStage','gemSlots',
                'footprints','suitStages','posters','personalities','uniques','limitAttrs','finishMapBigIds','skillSkins','guildSkills')
        inputs = {key:state.get(key) for key in keys}
        inputs['equipment'] = [e for e in state.get('equipment',[]) if e.get('generalId')]
        ship = state.get('shipyard',{})
        inputs['shipyard'] = {key:ship.get(key) for key in ('ships','charts','groups','lv','cabin','rooms')}
        inputs['teamLevel']=state.get('team',{}).get('lv',0)
        inputs['voyageTitle'] = state.get('voyage',{}).get('title',1)
        now = self.store.systems.now() if hasattr(self.store,'systems') else 0
        inputs['expired'] = [str(row.get('refId')) for key in ('footprints','personalities')
                             for row in state.get(key,{}).values()
                             if row.get('endTime') and row['endTime'] <= now]
        inputs['expiredLimits']=[key for key,row in state.get('limitAttrs',{}).items() if row.get('expiresAt',0)<=now]
        return json.dumps(inputs,sort_keys=True,separators=(',',':'))

    def evaluate(self, state):
        signature = self.signature(state)
        if signature == getattr(self,'_signature',None):
            return self._calculated
        result = self._evaluate(state)
        # Ship-room inheritance uses the donor's pre-inheritance six base
        # combat stats. The captured rate is known; this attr subset is local.
        inherited=defaultdict(lambda:defaultdict(float))
        for room in state.get('shipyard',{}).get('rooms',[]):
            ref=self.store.systems.rooms.get(int(room.get('roomRefId',room.get('refId',0))),{})
            donor=result.get(str(room.get('fromGeneral')));target=str(room.get('toGeneral'))
            if not donor or target not in result or target==str(room.get('fromGeneral')):continue
            for attr in range(1,7):inherited[target][attr]+=donor['values'].get(attr,0)*number(ref.get('rate'))/10000
        for gid,bonus in inherited.items():
            row=result[gid];bonus={key:math.floor(value) for key,value in bonus.items()}
            for key,value in bonus.items():row['values'][key]=row['values'].get(key,0)+value
            row['power']=math.floor(sum(value*number(self.refs.get(key,{}).get('rate')) for key,value in row['values'].items() if key!=1000));row['values'][1000]=row['power']
            row['attrs']=[{'key':self.refs[key]['attr'],'type':'double','doubleValue':value} for key,value in sorted(row['values'].items()) if key in self.refs]
            row['sources'].append({'source':'Ship room inheritance (pre-inheritance donor; local base-stat model)','attrs':bonus})
        self._signature, self._calculated = signature, result
        return result

    def _evaluate(self, state):
        store = self.store
        class_boost = defaultdict(lambda: defaultdict(float))
        for owned in state["generals"].values():
            for row in store.general_skills.get(owned["generalId"], []):
                scope = int(row["generalType"])
                if int(row["type"]) == 1 and scope and int(row["lock"]) <= owned["level"]:
                    for attr, value in attributes(row["attrs"]).items():
                        class_boost[scope][attr] += value
        party = defaultdict(float)
        # Owned companion attributes and completed books are crew-wide. Neither
        # owning a pet nor its appearance is fabricated by this calculation.
        for pet in state.get("pets", []):
            row = self.pet_stages.get((pet["refId"], int(pet.get("stage", pet.get("order", 1)))))
            for attr, value in attributes((row or {}).get("attrs", "")).items():
                party[attr] += value
        companion = state.get('companion', {})
        for table, field, key in [('PetBookStageRef', 'order', 'bookStage'), ('MountStageRef', 'refId', 'mountStage')]:
            if key == 'mountStage' and int(companion.get(key, 1)) <= 1:continue
            row = next((r for r in store.table(table) if int(r[field]) == int(companion.get(key, 0))), {})
            for attr, value in attributes(row.get('attrs', '')).items():party[attr] += value
        for table, owned_key, field in [("PetBookGroupRef", "pets", "petRefIds"), ("MountBookGroupRef", "mounts", "mountRefIds")]:
            owned_ids = {int(row["refId"]) for row in state.get(owned_key, [])}
            for row in store.table(table):
                required = {int(value) for value in row[field].split("#") if value}
                if required and required <= owned_ids:
                    for attr, value in attributes(row["attrs"]).items():
                        party[attr] += value
        for rid in companion.get('bookGroupPetIds',[]):
            for attr,value in attributes(store.pets.get(int(rid),{}).get('attrs','')).items():party[attr]+=value
        for row in store.table('TaskMapBigRef'):
            if int(row['refId']) in state.get('finishMapBigIds',[]):
                for attr,value in attributes(row.get('attrs','')).items():party[attr]+=value
        now=store.systems.now()
        limits={int(r['refId']):r for r in store.table('LimitAttrRef')}
        for key,owned in state.get('limitAttrs',{}).items():
            if owned.get('active') and owned.get('expiresAt',0)>now:
                for attr,value in attributes(limits.get(int(key),{}).get('attr','')).items():party[attr]+=value
        team=next((r for r in store.table('TeamLvRef') if int(r['lv'])==int(state.get('team',{}).get('lv',0))),{})
        for attr,value in attributes(team.get('attrs','')).items():party[attr]+=value
        for row in store.table('TeamSkillRef'):
            if str(row['refId']) in team.get('skillList','').split('#'):
                for attr,value in attributes(row.get('attrs','')).items():party[attr]+=value
        equipped_by_general=defaultdict(list)
        echo=self.store.systems.echo(state) if hasattr(self.store,'systems') else 0
        echo_row=next((r for r in self.store.table('GeneralEchoRef') if int(r['refId'])==echo),{})
        for equip in state['equipment']:
            if equip.get('generalId'):equipped_by_general[int(equip['generalId'])].append(equip)
        result = {}
        for general in state["generals"].values():
            gid = general["generalId"]
            definition = store.generals[gid]
            level = store.general_levels.get((gid, general["level"]), {})
            sources = [{"source": "GeneralLvRef", "attrs": {1: number(level.get("attack")), 2: number(level.get("hp")), 38: number(definition.get("speed", 72))}}]
            star = store.general_stars.get((gid, general["star"]), {})
            sources.append({"source": "GeneralStarRef (current cumulative row)", "attrs": attributes(star.get("attrs", ""))})
            sources.append({"source": "Owned crew level boosts for matching character class", "attrs": dict(class_boost[int(definition["type"])])})
            sources.append({"source": "Crew-wide pets, collections, reins, squad, claimed map bonuses and temporary attributes", "attrs": dict(party)})
            for mount in state.get('mounts',[]):
                if int(mount.get('generalId',0))!=gid:continue
                mount_definition=store.mounts.get(mount['refId'],{})
                for title,row in [('star',self.mount_stars.get((mount['refId'],int(mount.get('star',1))))),('level',self.mount_levels.get((int(mount_definition.get('order',0)),int(mount.get('level',1)))))]:
                    sources.append({'source':f'Assigned mount {mount["refId"]} {title}','attrs':attributes((row or {}).get('attrs',''))})
            skin_defs={int(r['skinId']):r for r in store.table('GeneralSkillSkinRef')}
            skin_stars={(int(r['skinId']),int(r['star'])):r for r in store.table('GeneralSkillSkinStarRef')}
            owned_skills=state.get('skillSkins',[])
            for owned in (owned_skills.values() if isinstance(owned_skills,dict) else owned_skills):
                rid=int(owned['refId'])
                if int(skin_defs.get(rid,{}).get('generalId',0))==gid:sources.append({'source':f'Owned skill skin {rid}','attrs':attributes(skin_stars.get((rid,int(owned['star'])),{}).get('attrs',''))})
            for row in store.table('GuildSkillLevelRef'):
                if int(row['type'])==int(definition['type']) and int(state.get('guildSkills',{}).get(str(row['guildSkillRefId']),-1))==int(row['level']):sources.append({'source':f'Guild skill {row["guildSkillRefId"]}','attrs':attributes(row['value'])})
            sources.append({'source':f'Active crew resonance {echo}','attrs':attributes(echo_row.get('attrs',''))})
            for node_id in self.potential_by_general[gid]:
                node_level = int(state["potential"].get(str(node_id), 0))
                row = store.potential_levels.get((node_id, node_level))
                if row:
                    sources.append({"source": f"PotentialLvRef {node_id}, level {node_level}", "attrs": attributes(row["attrs"])})
            for owned_skin in state.get('generalSkins',{}).values():
                skin_id=int(owned_skin['skinId'])
                if int(store.general_skins.get(skin_id,{}).get('generalId',0))!=gid:continue
                row=self.skins.get((skin_id,int(owned_skin.get('star',1))))
                if row:sources.append({'source':f'Owned skin {skin_id}','attrs':attributes(row['attrs'])})
            if hasattr(store,'systems'):sources.extend(store.systems.stat_sources(state,general))
            suits = defaultdict(int)
            for equip in equipped_by_general[gid]:
                row = store.equips.get(equip["equipRefId"], {})
                sources.append({"source": f"Equipment {equip['equipRefId']}", "attrs": attributes(row.get("attrs", ""))})
                if int(row.get("suitId", 0)):
                    suits[int(row["suitId"])] += 1
                for random_id in equip.get("randomAttrRefIds", []):
                    random = self.random.get(int(random_id), {})
                    sources.append({"source": f"Equipment random attributes {random_id}", "attrs": attributes(random.get("attrs", ""))})
            for row in store.table("EquipSuitNumRef"):
                if suits[int(row["refId"])] >= int(row["num"]):
                    sources.append({"source": f"Equipment set {row['refId']} ({row['num']} pieces)", "attrs": attributes(row["attrs"])})
            fruit = next((row for row in store.table("GeneralDevilFruitRef") if int(row["refId"]) == int(general.get("devilFruit", 0))), None)
            if fruit:
                sources.append({"source": "Equipped Devil Fruit", "attrs": attributes(fruit["attrs"])})
            if hasattr(store, "progression"):
                sources.extend(store.progression.stat_sources(state, general))
            if hasattr(store,'voyage'):
                title=int(state.get('voyage',{}).get('title',1))
                sources.append({'source':f'One Piece / Voyage title {title}','attrs':attributes(store.voyage.titles.get(title,{}).get('attrs',''))})
            raw = defaultdict(float)
            for source in sources:
                for attr, value in source["attrs"].items():
                    raw[attr] += value
            # Captured gear buckets have zero power rates. Fold their flat and
            # gear-specific percentage values into the six real combat stats.
            for base,bucket,rate in [(1,101,111),(2,201,211),(3,301,311),(4,401,411),(5,501,511),(6,601,611)]:
                raw[base]+=raw[bucket]*(1+raw[rate]/10000)
            final = dict(raw)
            for attr, value in raw.items():
                target = int(self.refs.get(attr, {}).get("useAttribute", 0))
                if target and target not in (101,201,301,401,501,601):
                    final[target] = final.get(target, 0) + raw[target] * value / 10000
            final = {attr: math.floor(value) for attr, value in final.items()}
            # Captured AttrRef display weights; cross-source stacking is local.
            power = math.floor(sum(value * number(self.refs.get(attr, {}).get("rate")) for attr, value in final.items() if attr != 1000))
            final[1000] = power
            attrs = [{"key": self.refs[attr]["attr"], "type": "double", "doubleValue": value} for attr, value in sorted(final.items()) if attr in self.refs]
            result[str(gid)] = {"generalId": gid, "level": general["level"], "star": general["star"], "power": power,
                                "attrs": attrs, "values": final, "sources": [source for source in sources if any(source["attrs"].values())],
                                "formula": "Sum flat attributes; apply captured percentages / 10000 to their useAttribute; sum final attributes × captured power rates.",
                                "fidelity": "Reference-driven local stacking model; exact production-server stacking is not available."}
        return result
