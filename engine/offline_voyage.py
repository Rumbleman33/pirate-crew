"""One Piece / Voyage title objectives, rewards, player level cap and bag sizes."""
class OfflineVoyage:
    handled_ids={2100,2101,2102,1112,1009}
    def __init__(self,store):
        self.store=store
        self.titles={int(r['refId']):r for r in store.table('VoyageTitleRef')}
        self.tasks=store.table('VoyageTaskRef')
    def fail(self,code,message):
        from offline_core import SimulationError
        raise SimulationError(code,message)
    def max_level(self,s):return int(self.titles.get(int(s.get('voyage',{}).get('title',1)),self.titles[1])['maxLevel'])
    def info(self,s):
        v=s.setdefault('voyage',{'title':1,'claims':[],'testCompletedTasks':[]})
        if v['title'] not in self.titles:v['title']=1
        tasks=[]
        for row in self.tasks:
            if int(row['titleRefId'])!=v['title']:continue
            fields=list(map(int,row['finishCondition'].split('_')));kind,need=fields[:2];rid=int(row['refId'])
            if kind==1:progress=s['player']['level']
            elif kind==32:progress=sum(g['level']>=fields[2] for g in s['generals'].values())
            elif kind==38:progress=sum(int(n) for k,n in s.get('progression',{}).get('kills',{}).items() if int(self.store.monsters.get(int(k),{}).get('type',0))==3)
            elif kind==40:progress=max(0,int(s.get('towerFloor',1))-1)
            elif kind==51:progress=int(s.get('progression',{}).get('gearForged',0))
            else:progress=0
            if s['settings'].get('autoVoyageObjectives',True) or rid in v.get('testCompletedTasks',[]):progress=max(progress,need)
            tasks.append({'refId':rid,'state':3 if s['settings'].get('autoVoyageObjectives',True) or rid in v['claims'] else 2 if progress>=need else 1,'progress':min(need,progress)})
        return {'title':v['title'],'tasks':tasks}
    def complete_test_tasks(self,s):
        info=self.info(s);s['voyage']['testCompletedTasks']=list(set(s['voyage'].get('testCompletedTasks',[]))|{t['refId'] for t in info['tasks']})
    def dispatch(self,s,cid,p):
        st=self.store
        if cid==1112:
            wanted=p.get('type') or list(range(7));result=[]
            for typ in wanted:
                typ=int(typ)
                if not 0<=typ<=6:self.fail('INVALID_BAG_TYPE','Choose a captured bag type.')
                if typ==2:cur=len(s['equipment'])
                else:
                    row=next(r for r in st.table('CapacityRef') if int(r['refId'])==typ)
                    types=set(row['type'].split('#'));cur=sum(int(n)>0 and st.items.get(int(rid),{}).get('type') in types for rid,n in s['inventory'].items())
                result.append({'type':typ,'max':-1 if typ==0 else max(10000,cur+100),'cur':cur})
            return {'capacities':result},False,'simulated'
        if cid==1009:
            level=int(s['player']['level']);row=st.player_levels.get(level)
            if level>=self.max_level(s):self.fail('VOYAGE_TITLE_REQUIRED','Upgrade One Piece / Voyage to raise the captain level cap.')
            costs=st._costs(row.get('exp','')) if row else []
            if not costs or int(s['inventory'].get('106',0))<costs[0][1]:self.fail('PLAYER_EXP_REQUIRED','More cumulative captain EXP is required.')
            s['player']['level']=level+1
            return {'newLevel':level+1,'reward':[]},True,'reference-driven'
        info=self.info(s);v=s['voyage']
        if cid==2100:return info,False,'reference-driven'
        if cid==2102:
            rid=int(p.get('taskRefId',0));task=next((r for r in info['tasks'] if r['refId']==rid),None)
            if not task or task['state']!=2:self.fail('VOYAGE_REWARD_NOT_READY','Complete this objective before claiming it.')
            row=next(r for r in self.tasks if int(r['refId'])==rid)
            reward=st._grant(s,row['reward']);v['claims'].append(rid);task['state']=3
            return {'task':task,'reward':reward},True,'reference-driven'
        nxt=int(self.titles[v['title']]['next'])
        if not nxt:self.fail('MAX_VOYAGE_TITLE','One Piece is at the captured maximum title.')
        rewards=[]
        if s['settings'].get('autoVoyageObjectives',True):
            for task in info['tasks']:
                if task['refId'] not in v['claims']:
                    row=next(r for r in self.tasks if int(r['refId'])==task['refId'])
                    rewards.extend(st._grant(s,row['reward']));v['claims'].append(task['refId'])
        elif not info['tasks'] or any(t['state']!=3 for t in info['tasks']):self.fail('VOYAGE_TASKS_REQUIRED','Complete and claim all current One Piece objectives first.')
        v['title']=nxt;reward=st._grant(s,self.titles[nxt].get('gift',''))
        return {**self.info(s),'reward':rewards+reward},True,'reference-driven'
