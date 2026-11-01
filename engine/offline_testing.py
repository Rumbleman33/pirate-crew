"""Explicit free sandbox presets; never purchase, claim, or change live data."""
import json
from copy import deepcopy


def apply(store, state, command, arg):
    if command=='endBossPractice':
        active=state.get('activeInstance')
        if active and active.get('practice') and str(active['data']['uid'])==str(arg):
            active['left']=True;store.encounters._archive(state,active);state.pop('activeInstance',None)
        return 'Boss practice closed; normal progression is unchanged.',None
    if command == 'talentLevel' or command == 'talentAll':
        maximum=max(int(r['level']) for r in store.progression.talents.values())
        level=maximum if command=='talentAll' else int(arg)
        if not 0<=level<=maximum:store.systems.fail('INVALID_TALENT_LEVEL',f'Choose talent level 0–{maximum}.')
        state['talent']={key:sorted(rid for rid,row in refs.items() if int(row['level'])<=level)
                         for key,refs in [('refIds',store.progression.talents),('advanceIds',store.progression.advanced_talents)]}
        state['settings']['testTalentLevel']=level
        return f'Talents set to level {level}; captain and character levels are separate.',{'type':'testingRefresh','system':'talent'}
    if command=='captainLevel':
        level=int(arg)
        if level not in store.player_levels:store.systems.fail('INVALID_PLAYER_LEVEL','Choose a captured captain level.')
        state['player']['level']=level
        return f'Captain level set to {level} for offline testing.',{'type':'testingRefresh','system':'captain'}
    if command=='charactersLevel':
        level=int(arg)
        if not 1<=level<=max(lv for gid,lv in store.general_levels):store.systems.fail('INVALID_GENERAL_LEVEL','Choose a captured character level.')
        for g in state['generals'].values():g['level']=max(lv for gid,lv in store.general_levels if gid==g['generalId'] and lv<=level)
        return f'Owned character levels set to {level}.',{'type':'testingRefresh','system':'characters'}
    if command=='maxHaki':
        for rid,part in {(rid,part) for rid,part,stage in store.systems.suits}:
            state['suitStages'][f'{rid}_{part}']={'refId':rid,'part':part,'stage':max(stage for key,p,stage in store.systems.suits if key==rid and p==part)}
    elif command=='maxPets':
        existing={p['refId']:p for p in state['pets']}
        for rid in store.pets:
            row=existing.setdefault(rid,{'refId':rid});row['stage']=max(stage for key,stage in store.companions.pet_rows if key==rid)
        state['pets']=list(existing.values());state['companion']['bookStage']=max(store.companions.book_rows)
        state['companion']['bookGroupPetIds']=sorted(store.pets)
    elif command=='maxMounts':
        existing={m['refId']:m for m in state['mounts']}
        for rid,ref in store.mounts.items():
            row=existing.setdefault(rid,{'refId':rid,'generalId':0,'use':False})
            row['star']=max(star for key,star in store.companions.star_rows if key==rid)
            row['level']=max(lv for key,lv in store.companions.level_rows if key==int(ref['order']))
        state['mounts']=list(existing.values());c=state['companion'];last=store.companions.rein_rows[-1]
        c.update(mountStage=int(last['refId']),reinExp=int(last['startExp']));state['inventory']['113']=c['reinExp']
        store.companions.repair(state)
    elif command=='maxTreasures':
        for rid in store.progression.treasures:
            star=max(star for key,star in store.progression.treasure_stars if key==rid)
            row=store.progression.treasure_stars[rid,star]
            limits=store.progression._limits(row.get('materialLimit',''))
            state['treasures'][str(rid)]={'refId':rid,'star':star,'materials':[{'refId':key,'count':n} for key,n in limits.items()]}
    elif command=='maxShips':
        b=state['shipyard'];systems=store.systems
        for rid in systems.ships:
            star=max(star for key,star in systems.ship_stars if key==rid);ref=systems.ship_stars[rid,star]
            limits=store.progression._limits(ref.get('materialLimit',''))
            b['ships'][str(rid)]={'refId':rid,'lv':star,'materials':[{'refId':key,'count':n} for key,n in limits.items()]}
        b['lv']=max(systems.docks);b['cabin']=max(systems.cabins)
        for rid in systems.charts:b['charts'][str(rid)]={'refId':rid,'star':max(star for key,star in systems.chart_levels if key==rid)}
        for gid in {key for key,star in systems.chart_groups}:b['groups'][str(gid)]={'refId':gid,'star':max(star for key,star in systems.chart_groups if key==gid)}
    elif command=='maxAllSystems':
        for cmd in ('maxPets','maxMounts','maxTreasures','maxShips'):apply(store,state,cmd,'')
        return 'Pets, mounts, treasures and ships maxed at their captured caps. Assign mounts and choose pet skills yourself.',{'type':'testingRefresh','system':'all'}
    elif command=='bossPractice':
        request=json.loads(arg);kind=request.get('kind');rid=int(request.get('id',0));catalog=boss_catalog(store)
        selected=next((r for r in catalog if r['kind']==kind and r['id']==rid),None)
        if not selected:store.systems.fail('UNKNOWN_PRACTICE_BOSS','Choose a captured boss from the selector.')
        # Use the authored tower arena, with the selected boss's captured stats,
        # skills and lineup. No arbitrary "level" scaling or progression rewards.
        generals=request.get('generals') or state['settings'].get('practiceGenerals') or [g['generalId'] for g in state['generals'].values() if g.get('isSelect')]
        capacity=store.progression.crew_capacity(state)
        if not isinstance(generals,list) or not 1<=len(generals)<=min(10,capacity) or len(set(generals))!=len(generals):store.systems.fail('INVALID_PRACTICE_LINEUP','Choose distinct owned fighters within your unlocked crew capacity.')
        for gid in generals:store._general(state,int(gid))
        state['settings']['practiceGenerals']=list(map(int,generals))
        active=store.encounters._make(state,201,1,generals,'practice',custom_waves=[{'wave':1,'data':'#'.join(f'{mid}_1_0_0_50' for mid in selected['monsterIds'])}])
        active.update(practice=True,practiceBoss=selected)
        return f'Practice: {selected["name"]}. No progression or rewards.',{'type':'bossPractice','data':deepcopy(active['data']),'name':selected['name'],'generalIds':generals}
    else:return None
    return f'{command[3:]} maxed at captured caps; assignments and other systems are preserved.',{'type':'testingRefresh','system':command[3:].lower()}


def boss_catalog(store):
    result=[]
    def add(kind,rid,ids,name):
        ids=[int(mid) for mid in ids if int(mid) in store.monsters]
        if ids:result.append({'kind':kind,'id':int(rid),'name':store.english(name),'monsterIds':ids,
                             'monsters':[{'id':mid,'name':store.english(store.monsters[mid].get('name','Boss')),'attrs':store.monsters[mid].get('attrs',''),'skills':store.monsters[mid].get('skill','')} for mid in ids]})
    for row in store.table('TowerLevelRef'):add('tower',row['refId'],row['monsterId'].split('#'),f'Impel Down floor {row["refId"]}')
    for row in store.table('RefreshMonsterRef'):
        if int(row['type'])==2:
            mid=int(row['monsterId']);add('map',row['refId'],[mid],f'{store.english(store.scenes.get(int(row["sceneId"]),{}).get("name",row["sceneId"]))} · {store.english(store.monsters.get(mid,{}).get("name",mid))}')
    for row in store.table('NpcRef'):
        if int(row['type'])==5 and int(row['bossId'])>0:add('challenge',row['refId'],[row['bossId']],f'{store.english(store.scenes.get(int(row["sceneId"]),{}).get("name",row["sceneId"]))} -> {store.english(store.scenes.get(int(row["data"]),{}).get("name",row["data"]))} · {store.english(store.monsters.get(int(row["bossId"]),{}).get("name",row["bossId"]))}')
    return result
