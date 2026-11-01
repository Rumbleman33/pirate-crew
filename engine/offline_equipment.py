"""Artifacts, equipment and bag actions using captured client contracts."""
from collections import defaultdict
import secrets


class OfflineEquipment:
    handled_ids={3500,3501,3502,1351,1352,1354,1355,1359,1360,1101,1102}

    def __init__(self, store):
        self.store=store
        self.unique={int(r['refId']):r for r in store.table('UniqueRef')}
        self.levels={(int(r['refId']),int(r['lv'])):r for r in store.table('UniqueLvRef')}

    def fail(self,code,message):
        from offline_core import SimulationError
        raise SimulationError(code,message)

    def entries(self,s,gid):
        result=[]
        for key,owned in s.get('uniques',{}).items():
            rid=int(key)
            if int(self.unique.get(rid,{}).get('generalId',0))!=gid:continue
            for (ref,level),row in self.levels.items():
                if ref==rid and level<=int(owned['lv']):
                    for entry in row.get('entry','').split('#'):
                        if entry:result.append(int(entry))
        return result

    def equip(self,s,value):
        e=next((r for r in s['equipment'] if str(r['equipId'])==str(value)),None)
        if not e:self.fail('UNKNOWN_EQUIPMENT','Select an owned equipment ID.')
        return e

    def rolls(self,row):
        count=int(row.get('randomAttrNum') or 0)
        pool=[r for r in self.store.table('EquipRandomAttrRef') if int(r.get('randomAttrIndex') or 0)==int(row.get('randomAttrIndex') or 0)]
        picked=[]
        for _ in range(min(count,len(pool))):
            r=self.store.workshop.pick(pool);pool.remove(r);picked.append(int(r['refId']))
        return picked

    def repair(self,s):
        if int(s['settings'].get('gearRepairVersion',0))>=1:return False
        # Remove phantom stack icons, retaining every actual equipment object.
        for rid in list(s['inventory']):
            if int(rid) in self.store.equips:s['inventory'].pop(rid)
        for equip in s['equipment']:
            row=self.store.equips.get(int(equip['equipRefId']),{})
            if not equip.get('randomAttrRefIds') and not int(row.get('needAuth') or 0):equip['randomAttrRefIds']=self.rolls(row)
            if int(row.get('needAuth') or 0) and not equip.get('randomAttrRefIds'):equip['generalId']=0
        s['settings']['gearRepairVersion']=1
        return True

    def dispatch(self,s,cid,p):
        st=self.store
        if cid in (3500,3501,3502):
            owned=s.setdefault('uniques',{})
            if cid==3500:return {'infos':list(owned.values())},False,'reference-driven'
            rid=int(p.get('refId',0));ref=self.unique.get(rid)
            if not ref:self.fail('UNKNOWN_ARTIFACT','Select a captured artifact.')
            st._general(s,int(ref['generalId']))
            current=owned.get(str(rid))
            if cid==3501:
                if current:self.fail('ALREADY_ACTIVE','This artifact is already active.')
                st._spend(s,ref['cost']);current={'refId':rid,'lv':1};owned[str(rid)]=current
            else:
                if not current:self.fail('ARTIFACT_NOT_ACTIVE','Activate this artifact first.')
                level=int(current['lv']);row=self.levels.get((rid,level))
                if not row or (rid,level+1) not in self.levels:self.fail('MAX_ARTIFACT_LEVEL','This artifact is at its captured maximum level.')
                st._spend(s,row['cost']);current['lv']=level+1
            return {'info':current},True,'reference-driven'
        if cid in (1351,1352,1355,1360):
            equip=self.equip(s,p.get('equipId'));changed=[]
            row=st.equips.get(int(equip['equipRefId']),{})
            if cid==1351:
                if int(row.get('needAuth') or 0) and not equip.get('randomAttrRefIds'):self.fail('GEAR_NOT_IDENTIFIED','Appraise this gear before equipping it.')
                gid=int(p.get('generalId',0));general=st._general(s,gid)
                if general['level']<int(row.get('needLevel',0)):self.fail('GEAR_LEVEL_REQUIRED','Character level is too low for this gear.')
                if int(row.get('generalType',0)) not in (0,int(st.generals[gid]['type'])):self.fail('GEAR_CLASS_REQUIRED','This gear belongs to a different character class.')
                for other in s['equipment']:
                    if other is not equip and int(other.get('generalId',0))==gid and st.equips[int(other['equipRefId'])]['part']==row['part']:
                        other['generalId']=0;changed.append(other)
                equip['generalId']=gid;changed.append(equip)
            elif cid==1352:equip['generalId']=0
            elif cid==1355:equip['lock']=not bool(equip.get('lock'))
            else:
                if equip.get('randomAttrRefIds'):self.fail('GEAR_ALREADY_IDENTIFIED','This gear is already identified.')
                count=int(row.get('randomAttrNum',0))
                if not int(row.get('needAuth',0)) or count<=0:self.fail('GEAR_NO_AUTH_REQUIRED','This equipment does not require identification.')
                pool=[r for r in st.table('EquipRandomAttrRef') if int(r.get('randomAttrIndex',0))==int(row.get('randomAttrIndex',0))]
                if len(pool)<count:self.fail('UNSUPPORTED_AUTH_POOL','The captured identification pool is incomplete; gear is unchanged.')
                picked=[]
                for _ in range(count):
                    r=st.workshop.pick(pool);pool.remove(r);picked.append(int(r['refId']))
                equip['randomAttrRefIds']=picked
            return {'equips':changed or [equip],'equip':equip},True,'reference-driven'
        if cid==1354:
            ids=p.get('equipIds')
            if not isinstance(ids,list) or not ids or len(ids)>1000:self.fail('INVALID_EQUIPMENT_SELECTION','Select 1–1,000 unequipped unlocked pieces.')
            selected=[self.equip(s,v) for v in dict.fromkeys(map(str,ids))]
            if any(e.get('lock') or e.get('generalId') for e in selected):self.fail('GEAR_PROTECTED','Unequip and unlock every selected piece first.')
            # Preserve the existing documented offline salvage payout until the
            # production-only breakdown is available; never consume protected gear.
            selected_ids={str(e['equipId']) for e in selected}
            s['equipment']=[e for e in s['equipment'] if str(e['equipId']) not in selected_ids]
            reward=st._grant(s,f'1_102_{100*len(selected)}')
            return {'equipIds':list(selected_ids),'reward':reward},True,'approximated'
        if cid==1359:
            rid=int(p.get('refId',0));recipe=next((r for r in st.table('EquipSuitCompoundRef') if int(r['refId'])==rid),None)
            ids=p.get('useEquipIds',[])
            if not recipe or not isinstance(ids,list) or len(set(map(str,ids)))!=int(recipe['fromCostNum']) or len(ids)!=int(recipe['fromCostNum']):self.fail('INVALID_SUIT_RECIPE','Choose the exact required number of distinct equipment pieces.')
            pieces=[self.equip(s,v) for v in ids]
            for e in pieces:
                r=st.equips[int(e['equipRefId'])]
                if e.get('lock') or e.get('generalId') or any(int(r[k])!=int(recipe[rk]) for k,rk in [('part','part'),('order','order'),('steps','fromSteps'),('star','fromStar')]):self.fail('INVALID_SUIT_MATERIAL','Suit ingredients must be unlocked, unequipped and match the captured recipe.')
            targets=[r for r in st.equips.values() if all(int(r[k])==int(recipe[rk]) for k,rk in [('part','part'),('order','order'),('steps','targetSteps'),('star','targetStar')])]
            if not targets:self.fail('MISSING_SUIT_TARGET','No captured target equipment for this recipe.')
            fails=s.setdefault('suitCraftFails',{});fail=int(fails.get(str(rid),0))
            success=secrets.randbelow(100)<min(100,int(recipe['baseSuccess'])+fail*int(recipe['failAddSuccess']))
            used=set(map(str,ids));sequence=max([int(e['equipId'])-8800000000000 for e in s['equipment']]+[0])+1
            s['equipment']=[e for e in s['equipment'] if str(e['equipId']) not in used]
            result={'vo':{'refId':rid,'failCount':0 if success else fail+1},'useEquipIds':list(used),'isSuccess':success}
            fails[str(rid)]=result['vo']['failCount']
            if success:
                equip=st._equip_vo(int(targets[secrets.randbelow(len(targets))]['refId']),sequence)
                s['equipment'].append(equip);result['equip']=equip
            return result,True,'reference-driven'
        rid=int(p.get('refId',0));count=int(p.get('useCount' if cid==1101 else 'count',p.get('saleCount',1)))
        if not 1<=count<=10000:self.fail('INVALID_ITEM_COUNT','Use a quantity from 1 to 10,000.')
        row=st.items.get(rid)
        if not row:self.fail('UNKNOWN_ITEM','Select a captured item.')
        if cid==1102:
            if not row.get('price'):self.fail('UNSUPPORTED_SALE','No captured sale price; nothing was consumed.')
            st._spend(s,f'1_{rid}_{count}');return {'reward':st._grant(s,row['price'],count)},True,'reference-driven'
        import time
        date=time.strftime('%Y-%m-%d',time.gmtime())
        uses=s.setdefault('itemDailyUses',{})
        used=int(uses.get(str(rid),{}).get('count',0)) if uses.get(str(rid),{}).get('date')==date else 0
        limit=int(row.get('dailyUseLimit') or 0)
        if limit and used+count>limit:self.fail('DAILY_ITEM_LIMIT','This quantity exceeds the captured daily use limit.')
        pools=[r for r in st.table('ItemRewardRef') if int(r['itemRefId'])==rid]
        rewards=defaultdict(int)
        if pools:
            kinds={int(r['type']) for r in pools}
            if kinds=={3}:
                options={int(r['rewardId']):r for r in pools};chosen={}
                for part in str(p.get('extParams','')).split('#'):
                    try:key,n=map(int,part.split('_'))
                    except ValueError:self.fail('ITEM_CHOICE_REQUIRED','Choose the rewards before opening this box.')
                    if key not in options or n<0:self.fail('INVALID_ITEM_CHOICE','The selected reward is not in this box.')
                    chosen[key]=chosen.get(key,0)+n
                if sum(chosen.values())!=count:self.fail('INVALID_ITEM_CHOICE','Selected reward counts must equal the boxes opened.')
                for key,n in chosen.items():
                    r=options[key]
                    for _ in range(n):rewards[key]+=int(r['min'])+secrets.randbelow(int(r['max'])-int(r['min'])+1)
            elif kinds=={1}:
                weight=sum(int(r['rate']) for r in pools)
                if weight<=0:self.fail('INVALID_REWARD_POOL','This captured reward pool has no weights.')
                for _ in range(count):
                    roll=secrets.randbelow(weight)
                    for r in pools:
                        roll-=int(r['rate'])
                        if roll<0:
                            rewards[int(r['rewardId'])]+=int(r['min'])+secrets.randbelow(int(r['max'])-int(r['min'])+1);break
            else:self.fail('UNSUPPORTED_REWARD_POOL','This reward pool type is not implemented; nothing was consumed.')
            encoded='#'.join(f'1_{key}_{value}' for key,value in rewards.items() if value)
        else:
            import re
            effect=row.get('effect','')
            if not effect or not re.fullmatch(r'1_\d+_\d+(#1_\d+_\d+)*',effect):self.fail('UNSUPPORTED_ITEM_EFFECT','This effect is not recovered; nothing was consumed.')
            encoded='#'.join(f'1_{key}_{value*count}' for key,value in st._costs(effect))
        # Check outputs before spending so unsupported rewards remain atomic.
        if any(key not in st.items and key not in st.generals for key,_ in st._costs(encoded)):self.fail('UNKNOWN_REWARD','A captured reward is unavailable; nothing was consumed.')
        st._spend(s,f'1_{rid}_{count}');result=st._grant(s,encoded)
        if any(r['refId']==106 for r in result):st._advance_player_level(s)
        uses[str(rid)]={'date':date,'count':used+count}
        return {'dailyUseCount':used+count,'rewards':result},True,'reference-driven'
