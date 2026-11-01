"""Captured fruit, ship, Haki, poster, path and appearance contracts.

Costs and cumulative rows are from the client. Cross-system stat stacking and
reset refunds are offline policies, not recovered production server logic.
"""
from collections import Counter
from copy import deepcopy
import time
from offline_stats import attributes

def num(v,default=0):
    try:return int(v)
    except (ValueError,TypeError):return default

class OfflineSystems:
    handled_ids={1308,1309,1310,1311,1318,1319,1550,1551,1552,2000,2001,2002,2003,2004,2005,2501,2502,2504,3400,3401,3403,3404,3405,3406,3407,3408,3409,3410,3411,3412,3414,3416,3417,10150,10151}
    def __init__(self,store):
        self.store=store
        self.fruits=self.index('GeneralDevilFruitRef');self.paths=self.index('GeneralFootprintRef')
        self.path_levels=self.index('GeneralFootprintStageRef','refId','stage')
        self.suits=self.index('SuitStageRef','refId','part','stageLv')
        self.posters=self.index('PirateReportRef');self.poster_levels=self.index('PirateReportLevelRef','refId','level')
        self.poster_types=self.index('PirateReportTypeRef');self.personalities=self.index('PersonalityRef')
        self.ships=self.index('ShipsRef');self.ship_stars=self.index('ShipsStarRef','refId','star')
        self.ship_materials=self.index('ShipsMaterialRef');self.docks=self.index('ShipsDockLvRef','lv')
        self.cabins=self.index('ShipsCabinRef','lv');self.charts=self.index('ShipNauticalChartRef')
        self.chart_levels=self.index('ShipNauticalChartLvRef','refId','star');self.chart_groups=self.index('ShipNauticalChartGroupRef','groupId','star')
        self.recipes=self.index('ShipsCookbookRef');self.rooms=self.index('ShipRoomRef')
    def index(self,name,*keys):
        keys=keys or ('refId',)
        return {(tuple(num(r[k]) for k in keys) if len(keys)>1 else num(r[keys[0]])):r for r in self.store.table(name)}
    def fail(self,code,message):
        from offline_core import SimulationError
        raise SimulationError(code,message)
    def now(self):return int(time.time()*1000)
    def repair(self,s):
        changed=False
        for skin in s.get('generalSkins',{}).values():
            if num(skin.get('star'))<1:skin['star']=1;changed=True
        defaults={'devilFruits':[],'footprints':{},'suitStages':{},'posters':{},'personalities':{}}
        for key,value in defaults.items():
            if key not in s:s[key]=deepcopy(value);changed=True
        for general in s['generals'].values():
            fruit=num(general.get('devilFruit'))
            if fruit in self.fruits and fruit not in s['devilFruits']:s['devilFruits'].append(fruit);changed=True
        now=self.now()
        for path in s['footprints'].values():
            if path['activeFlag'] and path['endTime'] and path['endTime']<=now:
                path['activeFlag']=False;changed=True
                for g in s['generals'].values():
                    if g.get('footprintId')==path['refId']:g['footprintId']=0
        for rid,row in self.personalities.items():
            if num(row.get('init')) and str(rid) not in s['personalities']:s['personalities'][str(rid)]={'refId':rid,'endTime':0,'activeFlag':True};changed=True
        for rid in s['player'].get('personality',{}).values():
            if num(rid) in self.personalities and str(rid) not in s['personalities']:s['personalities'][str(rid)]={'refId':num(rid),'endTime':0,'activeFlag':True};changed=True
        for owned in s['personalities'].values():
            if not owned.get('endTime') and not num(self.personalities.get(owned['refId'],{}).get('effectSecond')):owned['endTime']=4102444800000;changed=True
        personality=s['player']['personality']
        old=num(personality.get('mainRoleSkin'));background=num(personality.pop('backgroundRefId',0))
        if old and num(self.personalities.get(old,{}).get('type'))==5:personality['title']=old;personality['mainRoleSkin']=0;changed=True
        if background and num(self.personalities.get(background,{}).get('type'))==6:personality['mainRoleSkin']=background;changed=True
        if num(personality.get('mainRoleSkin')) not in self.personalities or num(self.personalities.get(num(personality.get('mainRoleSkin')),{}).get('type'))!=6:personality['mainRoleSkin']=60001;changed=True
        if '60001' not in s['personalities']:s['personalities']['60001']={'refId':60001,'endTime':4102444800000,'activeFlag':True};changed=True
        if 'shipyard' not in s:
            s['shipyard']={'ships':{},'lv':0,'cabin':0,'rooms':[],'charts':{},'groups':{},'cooking':{},'towerInfo':[],
                          'onHookInfo':{'lastRewardTime':now,'lastSettlementTime':now,'reward':[]}}
            changed=True
        return changed
    def ship_info(self,s):
        b=s['shipyard']
        return {k:list(b[k].values()) if k in ('charts','groups','cooking') else b[k] for k in ('lv','cabin','rooms','charts','groups','cooking','towerInfo','onHookInfo')}
    def roster(self,s,ids=None):
        return [g for g in self.store._roster(s) if ids is None or g['generalId'] in ids]
    def dispatch(self,s,cid,p):
        self.repair(s);st=self.store;rid=num(p.get('refId'))
        if 2000<=cid<=2005:return self.tower(s,cid,p)
        if cid==1310:return {'refIds':s['devilFruits']},False,'reference-driven'
        if cid==1311:
            if rid not in self.fruits:self.fail('UNKNOWN_FRUIT','Select a captured Devil Fruit.')
            if rid in s['devilFruits']:self.fail('ALREADY_ACTIVE','This Devil Fruit is already unlocked.')
            st._spend(s,self.fruits[rid]['cost']);s['devilFruits'].append(rid)
            return {'refId':rid},True,'reference-driven'
        if cid in (1308,1309):
            gid=num(p.get('generalId'));g=st._general(s,gid)
            if cid==1309:
                g['devilFruit']=0
                return {'general':self.roster(s,{gid})[0]},True,'reference-driven'
            fruit=num(p.get('devilFruit'))
            if fruit not in s['devilFruits']:self.fail('FRUIT_NOT_UNLOCKED','Unlock this Devil Fruit first.')
            definition=st.generals[gid]
            if num(definition.get('devilFruit'))!=1:self.fail('FRUIT_NOT_SUPPORTED','This character has no Devil Fruit slot in the captured game.')
            if g['star']<num(definition.get('devilFruitStar')):self.fail('FRUIT_STAR_REQUIRED','Raise this character to the captured Devil Fruit star requirement.')
            ids={gid}
            for other in s['generals'].values():
                if other.get('devilFruit')==fruit:other['devilFruit']=0;ids.add(other['generalId'])
            g['devilFruit']=fruit
            return {'generals':self.roster(s,ids)},True,'reference-driven'
        if cid in (1318,1319):
            ref=self.paths.get(rid)
            if not ref:self.fail('UNKNOWN_PATH','Choose a captured Path.')
            owned=s['footprints'].get(str(rid))
            if cid==1319:
                gid=num(p.get('generalId'));st._general(s,gid)
                if not owned or not owned['activeFlag']:self.fail('PATH_NOT_ACTIVE','Activate this Path first.')
                ids={gid}
                for g in s['generals'].values():
                    if g.get('footprintId')==rid:g['footprintId']=0;ids.add(g['generalId'])
                s['generals'][str(gid)]['footprintId']=rid
                return {'generals':self.roster(s,ids)},True,'reference-driven'
            timed=num(ref.get('effectSecond'))>0
            stage=num(owned.get('stage')) if owned else 0
            target=stage if timed and stage else stage+1
            row=self.path_levels.get((rid,target))
            if not row:self.fail('MAX_PATH_STAGE','This Path is at its captured maximum stage.')
            st._spend(s,row['cost'])
            owned={'refId':rid,'stage':target,'activeFlag':True,'endTime':max(self.now(),num((owned or {}).get('endTime')))+num(ref.get('effectSecond'))*1000 if timed else 0}
            s['footprints'][str(rid)]=owned
            return {'foorprint':owned},True,'reference-driven'
        if cid==1550:return {'infos':list(s['suitStages'].values())},False,'reference-driven'
        if cid in (1551,1552):
            part=num(p.get('part'));key=f'{rid}_{part}';current=s['suitStages'].get(key,{'refId':rid,'part':part,'stage':0})
            if cid==1552:
                if not current['stage']:self.fail('HAKI_NOT_ACTIVE','This Haki slot has not been activated.')
                # Exact refund percentage is unavailable: an offline reset refunds
                # the captured costs actually spent on this slot, without profit.
                rewards=[]
                for stage in range(1,current['stage']+1):rewards+=st._grant(s,self.suits[(rid,part,stage)]['cost'])
                current['stage']=0;s['suitStages'][key]=current
                return {'reward':rewards},True,'simulated'
            row=self.suits.get((rid,part,current['stage']+1))
            if not row:self.fail('MAX_HAKI_STAGE','This Haki slot is at its captured maximum stage.')
            st._spend(s,row['cost']);current['stage']+=1;s['suitStages'][key]=current
            return {'info':current},True,'reference-driven'
        if cid==10150:return {'infos':list(s['posters'].values())},False,'reference-driven'
        if cid==10151:
            current=s['posters'].get(str(rid),{'refId':rid,'level':0});row=self.poster_levels.get((rid,current['level']+1))
            if not row:self.fail('MAX_POSTER_LEVEL','Choose a captured poster that can still be upgraded.')
            st._spend(s,row['cost']);current['level']+=1;s['posters'][str(rid)]=current
            return {'info':current},True,'reference-driven'
        if cid==2501:return {'infos':list(s['personalities'].values())},False,'reference-driven'
        if cid in (2502,2504):
            row=self.personalities.get(rid)
            if not row:self.fail('UNKNOWN_APPEARANCE','Choose a captured title or appearance.')
            owned=s['personalities'].get(str(rid))
            if cid==2504:
                if owned and not num(row.get('effectSecond')):self.fail('ALREADY_ACTIVE','This appearance is already active.')
                st._spend(s,row.get('cost',''));seconds=num(row.get('effectSecond'))
                owned={'refId':rid,'endTime':max(self.now(),num((owned or {}).get('endTime')))+seconds*1000 if seconds else 4102444800000,'activeFlag':True}
                s['personalities'][str(rid)]=owned;st.encounters._push(s,2505,{'info':owned});return {'info':owned},True,'reference-driven'
            if not owned or not owned['activeFlag']:self.fail('APPEARANCE_NOT_ACTIVE','Activate this appearance first.')
            typ=num(p.get('type'));fields={2:'avatarRefId',3:'avatarFrameRefId',4:'chatFrameRefId',5:'title',6:'mainRoleSkin'}
            if typ not in fields or num(row['type'])!=typ:self.fail('WRONG_APPEARANCE_TYPE','Appearance type does not match.')
            s['player']['personality'][fields[typ]]=rid;st.encounters._push(s,2503,{'info':owned,'chooseInfo':s['player']['personality']});return {},True,'reference-driven'
        b=s['shipyard']
        if cid==3400:return self.ship_info(s),False,'reference-driven'
        if cid==3401:return {'ships':list(b['ships'].values())},False,'reference-driven'
        if cid==3403:
            current=b['ships'].get(str(rid),{'refId':rid,'lv':0,'materials':[]});row=self.ship_stars.get((rid,current['lv']+1))
            if rid not in self.ships or not row:self.fail('MAX_SHIP_STAR','Choose a captured ship that can be activated or upgraded.')
            st._spend(s,row['cost']);current['lv']+=1;b['ships'][str(rid)]=current
            return {'ship':current},True,'reference-driven'
        if cid==3404:
            ship=b['ships'].get(str(rid));material=p.get('addNum',{});mid,count=num(material.get('refId')),num(material.get('count'))
            if not ship or not 1<=count<=100000:self.fail('INVALID_SHIP_MATERIAL','Choose an active ship and a positive material quantity.')
            limits={num(a):num(c) for a,c in (r.split('_') for r in self.ship_stars[(rid,ship['lv'])]['materialLimit'].split('#') if r)}
            current=next((r for r in ship['materials'] if r['refId']==mid),{'refId':mid,'count':0})
            if mid not in limits or current['count']+count>limits[mid]:self.fail('SHIP_MATERIAL_LIMIT','This quantity exceeds the ship’s current star material limit.')
            st._spend(s,f'1_{mid}_{count}');current['count']+=count
            if current not in ship['materials']:ship['materials'].append(current)
            return {'info':current},True,'reference-driven'
        if cid in (3405,3414):
            key='lv' if cid==3405 else 'cabin';target=b[key]+1;row=self.docks.get(target) if cid==3405 else self.cabins.get(b[key])
            if not row or (cid==3414 and target not in self.cabins):self.fail('MAX_SHIP_FACILITY','This facility is at its captured maximum level.')
            st._spend(s,row.get('cost',''));b[key]=target
            return {'dockLv' if cid==3405 else 'cabin':target},True,'reference-driven'
        if cid in (3406,3407):
            rid=num(p.get('chartId'));ref=self.charts.get(rid);current=b['charts'].get(str(rid));star=num((current or {}).get('star'))+1
            row=self.chart_levels.get((rid,star))
            if not ref or not row:self.fail('MAX_CHART_STAR','Choose a captured chart that can still be upgraded.')
            if cid==3406 and current:self.fail('ALREADY_ACTIVE','This chart is already active.')
            if cid==3407 and not current:self.fail('CHART_NOT_ACTIVE','Activate this chart first.')
            st._spend(s,ref['cost'] if cid==3406 else row['cost']);current={'refId':rid,'star':star};b['charts'][str(rid)]=current
            return {'chart':current},True,'reference-driven'
        if cid==3408:
            rid=num(p.get('groupId'));star=num(b['groups'].get(str(rid),{}).get('star'))+1;row=self.chart_groups.get((rid,star))
            group=[num(c['refId']) for c in self.charts.values() if num(c['group'])==rid]
            if not row or not group:self.fail('MAX_CHART_RESONANCE','This chart group is at its captured maximum resonance.')
            if any(num(b['charts'].get(str(i),{}).get('star'))<num(row['needStar']) for i in group):self.fail('CHART_STARS_REQUIRED','Upgrade every chart in this group to the required star.')
            current={'refId':rid,'star':star};b['groups'][str(rid)]=current;return {'group':current},True,'reference-driven'
        if cid==3409:
            room=num(p.get('roomId'));fr,to=num(p.get('from')),num(p.get('to'))
            if room not in self.rooms:self.fail('UNKNOWN_SHIP_ROOM','Select a captured ship room.')
            if fr:st._general(s,fr)
            if to:st._general(s,to)
            if fr and fr==to:self.fail('DUPLICATE_ROOM_CHARACTER','Choose different characters for the two room positions.')
            if b['lv']<num(self.rooms[room]['lv']):self.fail('DOCK_LEVEL_REQUIRED','Upgrade the dock to unlock this room.')
            for entry in b['rooms']:
                for key in ('fromGeneral','toGeneral'):
                    if entry[key] in (fr,to) and entry[key]:entry[key]=0
            current=next((r for r in b['rooms'] if r['refId']==room),None)
            if current is None:current={'refId':room};b['rooms'].append(current)
            current.update(fromGeneral=fr,toGeneral=to)
            return {'rooms':b['rooms']},True,'reference-driven'
        if cid in (3410,3417):
            hook=b['onHookInfo'];rewards=[]
            if cid==3410:
                # Pending rewards are earned by local ship challenges. Empty
                # collections are valid and must still send a complete timer VO.
                if self.now()-hook['lastRewardTime']>=5*60000:
                    rewards=deepcopy(hook['reward']);hook['reward']=[];hook['lastRewardTime']=self.now();hook['lastSettlementTime']=self.now()
                    for item in rewards:st._grant(s,f"1_{item['refId']}_{item['count']}")
                return {'onHook':hook,'rewards':rewards},True,'simulated'
            return {'onHook':hook},False,'reference-driven'
        if cid in (3411,3412):
            slot=num(p.get('cookingId'));current=b['cooking'].get(str(slot),{'refId':slot,'cookbookId':0,'startTime':0,'count':0})
            if slot not in {num(r['refId']) for r in st.table('ShipsCookingRef')}:self.fail('UNKNOWN_COOKING_SLOT','Select a captured cooking slot.')
            if cid==3411:
                if current['count']:self.fail('COOKING_SLOT_BUSY','Collect this cooking slot before starting another recipe.')
                recipe=num(p.get('cookbookId'));count=num(p.get('count'));row=self.recipes.get(recipe)
                if not row or not 1<=count<=1000:self.fail('INVALID_COOKING_RECIPE','Choose a captured recipe and quantity from 1 to 1,000.')
                st._spend(s,row['cost'],count);current.update(cookbookId=recipe,startTime=self.now(),count=count);b['cooking'][str(slot)]=current
                return {'cooking':current},True,'reference-driven'
            if not current['count']:return {'cooking':current,'rewards':[]},False,'reference-driven'
            row=self.recipes[current['cookbookId']]
            if self.now()<current['startTime']+num(row['time'])*1000*current['count']:self.fail('COOKING_NOT_READY','The captured cooking timer has not finished.')
            rewards=st._grant(s,row['reward'],current['count']);current.update(cookbookId=0,startTime=0,count=0)
            return {'cooking':current,'rewards':rewards},True,'reference-driven'
        if cid==3416:
            ref=num(p.get('refId'));level=max(1,num(p.get('lv'),1));data=st.encounters._enter_instance(s,{'refId':ref,'lv':level,'generals':p.get('generals',[])})
            s['activeInstance']['shipChallenge']=True
            return {'data':data},True,'simulated'
        self.fail('UNSUPPORTED_SYSTEM','This system operation is not implemented.')
    def tower_info(self,s):
        tower=s.setdefault('tower',{'generals':[g['generalId'] for g in s['generals'].values() if g.get('isSelect')],'processIds':[],'rankReward':False})
        return {'refId':max(0,num(s.get('towerFloor'),1)-1),'generalIds':tower['generals'],'processIds':tower['processIds'],'rankReward':tower['rankReward']}
    def tower(self,s,cid,p):
        if s.get('activeInstance',{}).get('practice') and cid in (2002,2003):
            if cid==2003:s['activeInstance']['left']=True
            return ({'info':self.tower_info(s),'reward':[]} if cid==2003 else {}),cid==2003,'simulated'
        st=self.store;info=self.tower_info(s);tower=s['tower']
        if cid==2000:return {'info':info},False,'reference-driven'
        if cid==2001:
            ids=p.get('generalIds',[])
            if not isinstance(ids,list) or not 1<=len(ids)<=10 or len(set(map(num,ids)))!=len(ids):self.fail('INVALID_TOWER_TEAM','Select 1–10 distinct owned fighters.')
            for gid in ids:st._general(s,num(gid))
            tower['generals']=list(map(num,ids));return {'info':self.tower_info(s)},True,'reference-driven'
        if cid in (2002,2003):
            active=s.get('activeInstance')
            if not active or active['data']['refId']!=201:self.fail('NO_TOWER_CHALLENGE','Enter an Impel Down floor first.')
            if cid==2002:
                active['started']=True;active['data']['startTime']=st.encounters.now()
                return {},True,'reference-driven'
            if active.get('towerRewardClaimed'):return {'info':self.tower_info(s),'reward':[]},False,'reference-driven'
            success=bool(p.get('isWin'))
            if success and not (active.get('settled') and active.get('success')) and not st.encounters._all_waves_dead(active):self.fail('TOWER_NOT_CLEARED','Defeat every enemy before claiming this floor.')
            if not active.get('settled'):st.encounters._finish(s,active,success)
            floor=num(active['data']['lv']);rewards=[]
            if success and floor==num(s.get('towerFloor'),1):
                row=next((r for r in st.table('TowerLevelRef') if num(r['refId'])==floor),None)
                if not row:self.fail('UNKNOWN_TOWER_FLOOR','No captured reward for this floor.')
                rewards=st._grant(s,row['passReward']);s['towerFloor']=floor+1
            active['towerRewardClaimed']=True;active['left']=True
            st.encounters._archive(s,active)
            return {'info':self.tower_info(s),'reward':rewards},True,'reference-driven'
        if cid==2004:
            rid=num(p.get('processId'));row=next((r for r in st.table('TowerProcessRef') if num(r['refId'])==rid),None)
            if not row or rid>info['refId'] or rid in tower['processIds']:self.fail('TOWER_REWARD_NOT_READY','Clear the milestone before claiming it once.')
            rewards=st._grant(s,row['reward']);tower['processIds'].append(rid)
        else:
            if tower['rankReward'] or info['refId']<1:self.fail('TOWER_REWARD_NOT_READY','No new offline tower reward is available.')
            row=next((r for r in st.table('TowerRankRewardRef') if num(r['minRank'])<=info['refId']<=num(r['maxRank'])),None)
            if not row:self.fail('TOWER_REWARD_NOT_READY','No captured reward bracket for this floor.')
            rewards=st._grant(s,row['reward']);tower['rankReward']=True
        return {'info':self.tower_info(s),'reward':rewards},True,'simulated' if cid==2005 else 'reference-driven'
    def stat_sources(self,s,g):
        gid=g['generalId'];result=[]
        def add(label,row):
            if row and row.get('attrs'):result.append({'source':label,'attrs':attributes(row['attrs'])})
        for path in s.get('footprints',{}).values():
            if path['activeFlag'] and (not path['endTime'] or path['endTime']>self.now()):add('Activated Path',self.path_levels.get((path['refId'],path['stage'])))
        slots=s.get('suitStages',{}).values();counts=Counter((r['refId'],r['stage']) for r in slots if r['stage'])
        for slot in slots:add('Elemental Haki slot',self.suits.get((slot['refId'],slot['part'],slot['stage'])))
        for row in self.store.table('SuitNumRef'):
            if counts[(num(row['refId']),num(row['stageLv']))]>=num(row['num']):add('Haki equal-stage set',row)
        for poster in s.get('posters',{}).values():
            typ=num(self.posters.get(poster['refId'],{}).get('type'));targets=self.poster_types.get(typ,{}).get('generals','').split('#')
            if str(gid) in targets:add('Pirate Poster',self.poster_levels.get((poster['refId'],poster['level'])))
        for owned in s.get('personalities',{}).values():
            if owned['activeFlag'] and (not owned['endTime'] or owned['endTime']>self.now()):add('Activated appearance',self.personalities.get(owned['refId']))
        b=s.get('shipyard',{})
        ship_flat=Counter()
        for ship in b.get('ships',{}).values():
            if str(gid) not in self.ships.get(ship['refId'],{}).get('generals','').split('#'):continue
            star=self.ship_stars.get((ship['refId'],ship['lv']))
            add('Associated ship star',star)
            ship_flat.update(attributes((star or {}).get('attrs','')))
            for material in ship['materials']:
                attrs=attributes(self.ship_materials.get(material['refId'],{}).get('attrs',''));scaled={k:v*material['count'] for k,v in attrs.items()};ship_flat.update(scaled);result.append({'source':'Associated ship materials','attrs':scaled})
        for chart in b.get('charts',{}).values():add('Activated nautical chart',self.chart_levels.get((chart['refId'],chart['star'])))
        for group in b.get('groups',{}).values():add('Nautical chart resonance',self.chart_groups.get((group['refId'],group['star'])))
        add('Dock level',self.docks.get(num(b.get('lv'))))
        cabin=self.cabins.get(num(b.get('cabin')),{});add('Engine room cabin (local crew stacking)',cabin)
        result.append({'source':'Engine room associated-ship modifiers (local stacking)','attrs':{1:ship_flat[1]*num(cabin.get('atkRate'))/10000,2:ship_flat[2]*num(cabin.get('hpRate'))/10000}})
        return result
    def echo(self,s):
        eligible=[]
        for row in self.store.table('GeneralEchoRef'):
            count=sum(g['level']>=num(row['lv']) and num(self.store.generals.get(g['generalId'],{}).get('color'))>=num(row['quality']) for g in s['generals'].values())
            if count>=num(row['count']):eligible.append(row)
        return num(max(eligible,key=lambda r:num(r['order']))['refId']) if eligible else 0
