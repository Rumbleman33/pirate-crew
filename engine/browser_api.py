import json
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from offline_core import OfflineStore
from offline_draws import OfflineDraws
from offline_english import display_row
ROOT=Path('/pirates');STORE=OfflineStore(ROOT);DRAWS=OfflineDraws(STORE)
SESSION=ROOT/'runtime/browser-session.json';username=json.loads(SESSION.read_text()).get('username') if SESSION.exists() else None
def account():
 if not username:raise PermissionError('Sign into a browser test captain.')
 return username
def public_account():
 s=STORE.snapshot(account());return {'username':username,'playerId':s['playerId'],'displayName':s['player'].get('nickname',username),'gm':True,'mode':'offline'}
def dispatch(url,method,body):
 global username
 parsed=urlsplit(url);p=parsed.path;q=parse_qs(parsed.query);body=body or {}
 if p=='/api/login':
  auth=STORE.login(str(body.get('username','')).strip(),str(body.get('password','')))
  if not auth:return 401,{'detail':'Incorrect test username or password.'}
  username=auth['account']['username'];STORE.prepare_test_sandbox(username);SESSION.write_text(json.dumps({'username':username}));return 200,{'account':auth['account'],'mode':'offline'}
 if p=='/api/logout':username=None;SESSION.write_text('{}');return 200,{'ok':True}
 if p=='/api/health':return 200,{'ok':True,'mode':'offline','browserRuntime':True,'fullGM':True,'accountCount':len(STORE.accounts.list_accounts())}
 u=account()
 if p=='/api/me':result={'account':public_account(),'mode':'offline'}
 elif p in ['/api/me/snapshot','/api/state']:result=STORE.prepare_test_sandbox(u)
 elif p=='/api/command':result=STORE.command(u,int(body.get('id',0)),body.get('payload') or {})
 elif p=='/api/gm':result=STORE.gm(u,str(body.get('command','')),str(body.get('arg','')))
 elif p=='/api/battle':result=STORE.battle(u,int(body.get('monsterRefId',0)),min(100,max(1,int(body.get('count',1)))))
 elif p=='/api/stats':result=STORE.stats.evaluate(STORE.snapshot(u))
 elif p=='/api/world-maps':result=[display_row('SceneRef',r) for r in STORE.table('SceneRef') if 0<int(r['refId'])<100]
 elif p=='/api/testing/catalog':
  from offline_testing import boss_catalog
  result={'bosses':boss_catalog(STORE),'talentLevels':list(range(331)),'captainLevels':sorted(STORE.player_levels),'characterLevels':sorted({lv for gid,lv in STORE.general_levels})}
 elif p=='/api/gm-commands':result=STORE.gm_catalog()
 elif p=='/api/capabilities':result=STORE.capabilities()
 elif p=='/api/draw-lab/pools':result=DRAWS.catalog()
 elif p=='/api/draw-lab/run':result=DRAWS.simulate(body)
 elif p=='/api/export':result=STORE.export_save(u)
 elif p=='/api/import':result=STORE.import_save(u,body)
 elif p=='/api/reset':STORE.reset(u);result=STORE.prepare_test_sandbox(u)
 elif p=='/api/feature-audit':result=json.loads((ROOT/'data/feature-audit.json').read_text())
 elif p in ['/api/catalog','/api/schemas']:result=json.loads((ROOT/'data'/(p.rsplit('/',1)[1]+'.json')).read_text())
 elif p=='/api/references':result=[{'name':f.stem,'rows':len(STORE.table(f.stem))} for f in sorted((ROOT/'data/tables').glob('*.csv'))]
 elif p.startswith('/api/references/'):
  name=p.rsplit('/',1)[1];rows=[display_row(name,r) for r in STORE.table(name)];query=q.get('q',[''])[0].lower().strip()
  if query:rows=[r for r in rows if query in ' '.join(str(v) for v in r.values()).lower()]
  offset=max(0,int(q.get('offset',['0'])[0]));limit=min(500,max(1,int(q.get('limit',['100'])[0])))
  result={'table':name,'total':len(rows),'rows':rows[offset:offset+limit]}
 elif p=='/api/diagnostics':result={'mode':'offline','runtime':'Python/WebAssembly in this browser','saveStorage':'IndexedDB on this device','liveGameAccess':False}
 else:return 404,{'detail':'Browser API route unavailable: '+p}
 return 200,result
def request(raw):
 try:
  b=json.loads(raw);status,data=dispatch(b['url'],b.get('method','GET'),b.get('body'));return json.dumps({'status':status,'data':data})
 except PermissionError as e:return json.dumps({'status':401,'data':{'detail':str(e)}})
 except Exception as e:return json.dumps({'status':400,'data':{'detail':str(e),'errorType':type(e).__name__}})
