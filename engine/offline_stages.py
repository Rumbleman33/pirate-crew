"""Objective-based local practice for captured scripted solo dungeons.

Monster IDs, kill thresholds and completion rewards are captured. The original
server's area/NPC choreography and spawn locations were not recovered. Practice
waves spawn near the scene entrance and advance through the captured objectives.
"""
import json
from collections import Counter
from offline_systems import num

class OfflineStages:
    handled_ids={51010}
    def __init__(self,store):self.store=store
    def enter(self,s,ref,level,generals):
        st=self.store;rows=sorted((r for r in st.table('InsStageRef') if num(r['insId'])==ref),key=lambda r:num(r['stage']))
        required=Counter();waves=[];stage_numbers=[]
        for row in rows:
            current=Counter()
            for condition in row['condition'].split('&'):
                bits=condition.split('#')
                if len(bits)>=3 and num(bits[0])==4:current[num(bits[1])]=num(bits[2])
            entries=[]
            for mid,count in current.items():
                extra=max(0,count-required[mid]);required[mid]=max(required[mid],count)
                if extra:entries.append(f'{mid}_{extra}_0_0_90')
            if entries:waves.append({'wave':len(waves)+1,'data':'#'.join(entries)});stage_numbers.append(num(row['stage']))
        finish=st.instances[ref].get('finishParam','').replace('#','_').split('_')
        if len(finish)>=3 and num(finish[0])==6 and num(finish[1]) in st.monsters:
            waves.append({'wave':len(waves)+1,'data':f'{num(finish[1])}_{max(1,num(finish[2]))}_0_0_60'});stage_numbers.append(max([num(r['stage']) for r in rows]+[1]))
        if not waves:
            from offline_core import SimulationError
            raise SimulationError('UNSUPPORTED_STAGE_OBJECTIVES','No captured combat objectives were recovered for this solo dungeon.')
        active=st.encounters._make(s,ref,level,generals,'stage-practice',custom_waves=waves)
        active.update(stagePractice=True,stageNumbers=stage_numbers,stageKills={})
        self.publish(s,active)
        return active
    def value(self,active):
        stage=active.get('stageNumbers',[1])[min(active.get('waveIndex',0),len(active.get('stageNumbers',[1]))-1)]
        return {'stage':stage,'skills':[],'box':[],'npc':[],'unlockAreaIds':[],'bhvData':[],'monsterDeadCount':[{'key':num(k),'vaule':n} for k,n in active.get('stageKills',{}).items()],'itemList':[]}
    def publish(self,s,active):
        self.store.encounters._push(s,51009,{'type':9,'data':[],'playerId':s['playerId'],'_offlinePayload':{'schema':'CmdSettlementStage','field':'data','value':self.value(active)}})
    def dispatch(self,s,cid,p):
        active=s.get('activeInstance')
        if not active or not active.get('stagePractice'):
            from offline_core import SimulationError
            raise SimulationError('NO_SOLO_DUNGEON','Enter a solo dungeon first.')
        # Practice has no fabricated reward chests or item-consuming NPCs.
        # Captured combat objectives control progress and final settlement.
        self.publish(s,active)
        return {'resultJson':json.dumps({'offlinePractice':True,'stage':self.value(active)['stage']})},True,'simulated'
