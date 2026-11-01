"""Local fleet/squad, treasure collections and Secret Chamber lifecycle.

Fleet and squad members are local to the save. Online friend/lobby state is a
separate service. Encounter arbitration remains an explicit offline simulation.
"""
from copy import deepcopy
import time
from offline_systems import num

class OfflineWorld:
    handled_ids={2902,2904,2908,2909,2911,2914,2916,2919,2922,2924,2927,30001,30002,30003,30004,30006,30011,30016,10160,10161,10162,50201,50202,54001,54002,54003,54006}
    def __init__(self,store):self.store=store
    def now(self):return int(time.time()*1000)
    def fail(self,code,text):
        from offline_core import SimulationError
        raise SimulationError(code,text)
    def name(self,value,limit=16):
        value=str(value or '').strip()
        if not 2<=len(value)<=limit:self.fail('INVALID_NAME',f'Use a name of 2–{limit} characters.')
        return value
    def identity(self,s):
        p=s['player'];gid=next((g['generalId'] for g in s['generals'].values() if g.get('isSelect')),2000001)
        return {'playerId':s['playerId'],'playerName':p['nickname'],'name':p['nickname'],'personality':p['personality'],'level':p['level'],'lv':p['level'],'vipLevel':p['vipLevel'],'vipLv':p['vipLevel'],'serverId':1,'power':sum(a['attrValue'] for a in p['attrs'] if a['attrType']==1000),'generalId':gid,'online':True,'offlineTime':0,'generalSkin':0}
    def guild_info(self,s):
        if not s.get('guild'):return {}
        base=s['guild'];me=self.identity(s)
        return {'type':1,'guild':{'guild':base,'presidentName':me['name'],'guildExp':0,'dailyGuildExp':0,'bulletin':base.get('declaration',''),'disbandTime':0,'presidentId':s['playerId'],'lastRecruitTime':0}}
    def team_player(self,s):return {'appliedTeamList':[],'lvRewards':[],'bossRewards':[],'bossTime':0,'donate':[],'lastBossRewardTime':0}
    def dispatch(self,s,cid,p):
        st=self.store
        if 2900<=cid<3000:
            if cid==2902:
                if s.get('guild'):self.fail('ALREADY_IN_FLEET','This captain already has a local fleet.')
                cfg=st.table('GuildConfigRef')[0];name=self.name(p.get('name'),num(cfg['nameMaxLen'],12));st._spend(s,cfg['createCost'])
                s['guild']={'guildId':s['playerId']+1000000,'name':name,'level':1,'memberCount':1,'autoApply':bool(p.get('autoApply')),'declaration':str(p.get('declaration',''))[:120],'badgeRefId':num(p.get('badgeRefId'),1),'baseMapRefId':num(p.get('baseMapRefId'),1),'rank':1,'power':self.identity(s)['power'],'createTime':self.now(),'serverId':1}
                return {'guildInfo':self.guild_info(s)},True,'simulated'
            if cid==2904:return {'appliedGuildIds':[],'nextCanApplyTime':0,'bossRewardCount':0,'lastQuitTime':0,**({'guildInfo':self.guild_info(s)} if s.get('guild') else {})},False,'simulated'
            if cid==2908:return {'memberInfos':[{'baseInfo':{**self.identity(s),'guildId':s['guild']['guildId']},'type':1,'guildContribution':0,'weeklyGuildContribution':0,'enterTime':s['guild']['createTime']}] if s.get('guild') else []},False,'simulated'
            if cid==2911:s.pop('guild',None);return {},True,'simulated'
            if cid==2909:
                if not s.get('guild'):self.fail('NO_FLEET','Create a local fleet first.')
                typ=num(p.get('type'));field={1:'name',2:'declaration',3:'autoApply',4:'badgeRefId',5:'bulletin'}.get(typ)
                if not field:self.fail('INVALID_FLEET_FIELD','Choose a supported fleet setting.')
                value=p.get('param','')
                if field=='name':value=self.name(value,12);st._spend(s,st.table('GuildConfigRef')[0]['changeNameCost'])
                elif field=='autoApply':value=str(value).lower() in ('1','true')
                elif field=='badgeRefId':value=num(value)
                else:value=str(value)[:120]
                s['guild'][field]=value;return {'guildInfo':self.guild_info(s)},True,'simulated'
            if cid==2916:return {'boxRefIds':[],'constructInfos':[],'logs':[]},False,'simulated'
            if cid==2919:return {'skills':[]},False,'simulated'
            if cid==2922:return {'guilds':[s['guild']] if s.get('guild') else []},False,'simulated'
            return {},False,'simulated'
        if 30000<cid<30100:
            if cid==30003:
                if s.get('team'):self.fail('ALREADY_IN_SQUAD','This captain already has a local squad.')
                cfg=st.table('TeamConfigRef')[0];name=self.name(p.get('name'),num(cfg['nameLmt'],16));st._spend(s,cfg['cost'])
                me=self.identity(s);member={**me,'id':s['playerId'],'avatarRefId':s['player']['personality']['avatarRefId'],'avatarFrameRefId':s['player']['personality']['avatarFrameRefId'],'title':s['player']['personality'].get('title',0)}
                s['team']={'id':s['playerId']+2000000,'name':name,'desc':'Local offline test squad','lv':1,'avatarRefId':num(p.get('avatarRefId'),member['avatarRefId']),'leaderId':s['playerId'],'members':[{'base':member,'generals':st._roster(s)}],'serverId':1,'curBossId':1,'lessHp':10000,'exp':0,'autoJoin':False,'dissolve':False,'maxBossId':0,'inspireExpired':0,'createTime':self.now(),'serverStartTime':s['player'].get('openServerTime',0)}
                return {'team':s['team']},True,'simulated'
            if cid==30001:return {'teamPlayer':self.team_player(s),**({'team':s['team']} if s.get('team') else {})},False,'simulated'
            if cid==30002:return {'teams':[s['team']] if s.get('team') else []},False,'simulated'
            if cid==30004:
                if not s.get('team'):self.fail('NO_SQUAD','Create a local squad first.')
                for key in ('name','desc','avatarRefId','autoJoin'):
                    if key not in p:continue
                    value=p[key]
                    if key=='name':value=self.name(value)
                    elif key=='desc':value=str(value)[:50]
                    elif key=='avatarRefId':value=num(value)
                    else:value=bool(value)
                    s['team'][key]=value
                return {'team':s['team']},True,'simulated'
            if cid==30006:return {'member':[]},False,'simulated'
            if cid==30011:return {'infos':[]},False,'simulated'
            if cid==30016:return {'stage':0,'report':False,'rank':0,'stageId':0,'startStageTime':0,'endStageTime':0,'team':[],'winTeamId':0,'state':0,'records':[]},False,'simulated'
        if cid in (10160,10161,10162):return self.rare(s,cid,p)
        if cid in (50201,50202):return self.box(s,cid,p)
        if cid in (54001,54002,54003,54006):return self.brawl(s,cid,p)
        self.fail('UNSUPPORTED_WORLD_ACTION','This local world operation is not implemented.')
    def rare(self,s,cid,p):
        st=self.store;day=time.strftime('%Y-%m-%d',time.gmtime());save=s.setdefault('rare',{});configs={num(r['refId']):r for r in st.table('RareConfigRef')}
        for rid in configs:
            info=save.setdefault(str(rid),{'type':rid,'dailyFreeCount':0,'continueCount':0,'countRewardIds':[],'day':day})
            if info['day']!=day:info['day']=day;info['dailyFreeCount']=0
        if cid==10160:return {'rareInfos':list(save.values())},False,'reference-driven'
        typ=num(p.get('rareType'));cfg=configs.get(typ);info=save.get(str(typ))
        if not cfg:self.fail('UNKNOWN_TREASURE_HUNT','Choose the captured pet or mount treasure hunt.')
        if cid==10162:
            rid=num(p.get('refId'));row=next((r for r in st.table('RareCountRewardRef') if num(r['refId'])==rid and num(r['configId'])==typ),None)
            if not row or info['continueCount']<num(row['count']) or rid in info['countRewardIds']:self.fail('HUNT_REWARD_NOT_READY','Reach the draw milestone before claiming it once.')
            reward=st._grant(s,row['reward']);info['countRewardIds'].append(rid);return {'rareInfo':info,'reward':reward},True,'reference-driven'
        count=num(p.get('buyType'))
        if count not in (1,10):self.fail('INVALID_DRAW_COUNT','Choose one or ten draws.')
        age=num(s['settings'].get('serverAgeDays'),365)
        pool=[r for r in st.table('RareItemGroupRef') if num(r['group'])==num(cfg['normalGroup']) and (num(r['openDays'])<0 or age>=num(r['openDays'])) and (num(r['endDays'])<0 or age<=num(r['endDays']))]
        if not pool:self.fail('EMPTY_DRAW_POOL','No captured reward pool matches this server age.')
        if count==1 and info['dailyFreeCount']<num(cfg['dailyFreeCount']):info['dailyFreeCount']+=1
        else:
            item=cfg['itemTenCost' if count==10 else 'itemCost'];cost=cfg['tenCost' if count==10 else 'cost']
            if item and all(num(s['inventory'].get(str(r)))>=n for r,n in st._costs(item)):cost=item
            st._spend(s,cost)
        reward=[]
        for _ in range(count):reward+=st._grant(s,st.workshop.pick(pool)['reward'])
        info['continueCount']+=count
        return {'rareInfo':info,'reward':reward},True,'reference-driven'
    def box(self,s,cid,p):
        st=self.store;scene=num(p.get('sceneId'),num(s['scene']['mapId']));save=s.setdefault('worldBoxes',{})
        if str(scene) not in save:
            refs=[r for r in st.table('BoxRef') if num(r.get('sceneId'))==scene and not num(r.get('productId'))]
            positions=[r for r in st.table('BoxPosRef') if num(r['sceneId'])==scene]
            entries=[]
            for i,pos in enumerate(positions[:3]):
                if not refs:break
                ref=refs[i%len(refs)];entries.append({'uid':scene*100000+num(pos['refId']),'refId':num(ref['refId']),'expire':0,'x':num(pos['x']),'y':num(pos['y']),'sceneId':scene,'open':False,'rewards':[]})
            save[str(scene)]={'count':0,'boxes':entries}
        data=save[str(scene)]
        if cid==50201:return {'sceneCount':data['count'],'vos':[r for r in data['boxes'] if not r['open']],'onceBoxId':[],'limitBox':[],'payBoxId':[]},False,'simulated'
        uid=num(p.get('uid'));box=next((r for r in data['boxes'] if r['uid']==uid),None)
        if not box or box['open']:self.fail('BOX_ALREADY_COLLECTED','This treasure has already been collected or is not in this scene.')
        ref=next(r for r in st.table('BoxRef') if num(r['refId'])==box['refId'])
        active={'data':{'uid':uid}};rewards=st.encounters._grant(s,ref['reward'],active,'world-box')
        box['open']=True;box['rewards']=rewards;data['count']+=1
        return {'sceneCount':data['count'],'rewards':rewards},True,'simulated'
    def brawl_info(self,s,layer=0):
        result=[]
        for sub in self.store.table('BrawlSubRef'):
            if layer and num(sub['layer'])!=layer:continue
            for row in self.store.table('BrawlRefreshRef'):
                if num(row['layer'])!=num(sub['layer']):continue
                result.append({'subActivityId':sub['subId'],'bossRefId':num(row['refId']),'nextRefreshTime':0,'hpRate':10000})
        return result
    def brawl_dead(self,s,active,target):
        paid=active.setdefault('brawlPaid',[])
        if target['uid'] in paid:return
        row=next((r for r in self.store.table('BrawlRefreshRef') if num(r['refId'])==target['id']),None)
        if not row:return
        rewards=self.store.encounters._grant(s,row['reward'],active,f"brawl-boss-{target['uid']}")
        paid.append(target['uid'])
        self.store.encounters._push(s,54007,{'playerId':s['playerId'],'playerName':s['player']['nickname'],'bossId':target['id'],'bossName':self.store.english(self.store.monsters[target['id']].get('name','Boss')),'reward':rewards})
    def brawl(self,s,cid,p):
        st=self.store
        if cid in (54001,54006):return {'info':self.brawl_info(s,num(p.get('layer'))),'serverId':[],'dailyHonorCount':0,'dailyCount':0},False,'simulated'
        subid=str(p.get('subActivityId',''));sub=next((r for r in st.table('BrawlSubRef') if r['subId']==subid),None)
        if not sub:self.fail('UNKNOWN_CHAMBER','Choose a captured Secret Chamber layer.')
        if cid==54003:
            active=s.get('activeInstance')
            if active and active.get('brawlSubId')==subid:active['left']=True;st.encounters._archive(s,active)
            return {'subActivityId':subid},True,'simulated'
        ref=num(sub['insId']);old=st.encounters._ensure_available(s,'brawl',ref,1,sub_id=None)
        if old:return {'data':old['data'],'type':3,'settlementData':[],'_offlinePayload':{'schema':'CmdSettlementBrawl','value':{'bossInfo':self.brawl_info(s,num(sub['layer']))}}},False,'simulated'
        rows=[r for r in st.table('BrawlRefreshRef') if num(r['layer'])==num(sub['layer'])]
        wave={'wave':'1','data':'#'.join(f"{r['refId']}_1_{r['x']}_{r['y']}_30" for r in rows)}
        active=st.encounters._make(s,ref,1,p.get('generals',[]),'brawl',custom_waves=[wave]);active.update(brawlSubId=subid,keepOpen=True,brawlPaid=[])
        return {'data':active['data'],'type':3,'settlementData':[],'_offlinePayload':{'schema':'CmdSettlementBrawl','value':{'bossInfo':self.brawl_info(s,num(sub['layer']))}}},True,'simulated'
