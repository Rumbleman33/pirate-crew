import unittest,sys,json
from pathlib import Path
from copy import deepcopy
sys.path.insert(0,str(Path(__file__).parent))
import test_tester_fixes as fixture
from offline_testing import boss_catalog

class TestingPresets(unittest.TestCase):
 @classmethod
 def setUpClass(cls):fixture.TesterRegressionTests.setUpClass.__func__(cls)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def setUp(self):self.store.reset('pirate01');self.store.prepare_test_sandbox('pirate01')
 def state(self):return self.store.snapshot('pirate01')
 def gm(self,cmd,arg=''):
  result=self.store.gm('pirate01',cmd,str(arg));self.assertTrue(result['ok'],result.get('error'));return result
 def test_talents_exact_target_and_captain_separate(self):
  self.gm('talentLevel',115);s=self.state();self.assertEqual(s['player']['level'],1)
  self.assertTrue(all(int(self.store.progression.talents[r]['level'])<=115 for r in s['talent']['refIds']))
  self.gm('talentAll');self.assertEqual(len(self.state()['talent']['refIds']),990)
  self.gm('talentLevel',0);self.assertEqual(self.state()['talent']['refIds'],[])
  self.gm('captainLevel',115);self.assertEqual(self.state()['player']['level'],115)
  self.assertFalse(self.store.gm('pirate01','talentLevel','331')['ok'])
 def test_max_all_caps_preserves_costs_assignments_and_is_idempotent(self):
  before=self.state()['inventory'];self.gm('maxAllSystems');s=self.state()
  self.assertEqual(len(s['pets']),len(self.store.pets));self.assertTrue(all(p['stage']==10 for p in s['pets']))
  self.assertTrue(all(m['star']==10 and m['level']==200 and not m['generalId'] for m in s['mounts']))
  self.assertTrue(all(t['star']==30 for t in s['treasures'].values()))
  self.assertEqual(len(s['shipyard']['ships']),len(self.store.systems.ships))
  self.assertEqual(s['shipyard']['lv'],max(self.store.systems.docks))
  for key,value in before.items():
   if key!='113':self.assertEqual(s['inventory'][key],value)
  for key in ('pets','mounts','treasures','shipyard'):before[key]=deepcopy(s[key])
  self.gm('maxAllSystems');s=self.state()
  for key in ('pets','mounts','treasures','shipyard'):self.assertEqual(s[key],before[key])
 def test_mount_stats_only_reach_assigned_character(self):
  self.gm('maxMounts');s=self.state();gids=list(s['generals'])[:2];before=self.store.stats.evaluate(s)
  s['mounts'][0]['generalId']=int(gids[0]);s['mounts'][0]['use']=True;after=self.store.stats.evaluate(s)
  self.assertGreater(after[gids[0]]['power'],before[gids[0]]['power']);self.assertEqual(after[gids[1]]['power'],before[gids[1]]['power'])
  s['mounts'][0]['generalId']=0;s['mounts'][0]['use']=False;self.assertEqual(self.store.stats.evaluate(s)[gids[0]]['power'],before[gids[0]]['power'])
 def test_promote_repeatedly_without_claims_and_never_duplicate_old_rewards(self):
  s=self.state();self.assertTrue(all(t['state']==3 for t in self.store.voyage.info(s)['tasks']))
  for _ in range(3):
   result=self.store.command('pirate01',2101,{});self.assertTrue(result['ok'],result.get('error'))
  s=self.state();self.assertEqual(s['voyage']['title'],4);self.assertEqual(len(s['voyage']['claims']),len(set(s['voyage']['claims'])))
 def test_boss_catalog_and_practice_no_progress_or_rewards(self):
  rows=boss_catalog(self.store);self.assertEqual({r['kind'] for r in rows},{'tower','map','challenge'})
  for kind in ('tower','map','challenge'):
   row=next(r for r in rows if r['kind']==kind);before=self.state();self.gm('bossPractice',json.dumps({'kind':kind,'id':row['id']}));s=self.state();active=s['activeInstance']
   self.assertEqual([r['id'] for r in active['data']['sprites'] if r['type']==2],row['monsterIds'])
   self.assertEqual(len([r for r in active['data']['sprites'] if r['type']==1]),2)
   for enemy in active['data']['sprites']:
    if enemy['type']==2:enemy['labile']['hp']['cur']=0
   self.store.encounters._finish(s,active);self.store._write('pirate01',s);s=self.state()
   self.assertEqual(s['inventory'],before['inventory']);self.assertEqual(s['towerFloor'],before['towerFloor']);self.assertEqual(s['instanceLevels'],before['instanceLevels']);self.assertEqual(active['data']['rewards'],[])
 def test_upgrade_backup_preserves_identity_equipment_and_progress(self):
  s=self.state();s['saveSchemaVersion']=13;s['settings']['customSaveMarker']='retained';self.store._write('pirate01',s)
  backup=self.store.saves.parent/'backups/pirate01-before-v14.json'
  if backup.exists():backup.unlink()
  restored=self.state();self.assertTrue(backup.exists());self.assertEqual(restored['settings']['customSaveMarker'],'retained');self.assertEqual(restored['equipment'],s['equipment']);self.assertEqual(restored['playerId'],s['playerId'])
  self.assertEqual(json.loads(backup.read_text())['saveSchemaVersion'],13)
 def test_temporary_stats_expire_and_cache_invalidates(self):
  from unittest.mock import patch
  s=self.state();before=self.store.stats.evaluate(s);self.gm('limitAttr',1);s=self.state()
  current=self.store.stats.evaluate(s);gid=next(iter(s['generals']));self.assertGreater(current[gid]['values'][1],before[gid]['values'][1])
  self.assertEqual(s['limitAttrs']['1']['expiresAt']-s['limitAttrs']['1']['activatedAt'],900000)
  with patch.object(self.store.systems,'now',return_value=s['limitAttrs']['1']['expiresAt']+1):self.assertEqual(self.store.stats.evaluate(s)[gid]['power'],before[gid]['power'])
 def test_ship_room_inheritance_is_local_to_receiver_and_nonrecursive(self):
  s=self.state();gids=list(s['generals']);before=self.store.stats.evaluate(s)
  s['shipyard']['rooms']=[{'refId':1,'fromGeneral':int(gids[0]),'toGeneral':int(gids[1])}]
  after=self.store.stats.evaluate(s);self.assertEqual(after[gids[0]]['power'],before[gids[0]]['power']);self.assertEqual(after[gids[1]]['values'][1],before[gids[1]]['values'][1]+int(before[gids[0]]['values'][1]*.1))
 def test_current_squad_level_and_claimed_maps_have_independent_bonuses(self):
  s=self.state();gid=next(iter(s['generals']));before=self.store.stats.evaluate(s)[gid]
  s['team']={'lv':1};after=self.store.stats.evaluate(s)[gid];self.assertEqual(after['values'][1]-before['values'][1],30);self.assertEqual(after['values'][2]-before['values'][2],500)
  s['finishMapBigIds']=[10001];claimed=self.store.stats.evaluate(s)[gid];self.assertGreater(claimed['power'],after['power'])
 def test_skill_skin_and_display_only_fruit_power(self):
  s=self.state();gid=2000004;s['generals'][str(gid)]=self.store._general_vo(gid,1,0);before=self.store.stats.evaluate(s)[str(gid)]
  s['skillSkins']=[{'refId':1001,'star':1}];skin=self.store.stats.evaluate(s)[str(gid)];self.assertGreater(skin['power'],before['power'])
  s['generals'][str(gid)]['devilFruit']=7000001;fruit=self.store.stats.evaluate(s)[str(gid)];self.assertEqual(fruit['values'][1],skin['values'][1]);self.assertEqual(fruit['values'][2],skin['values'][2]);self.assertEqual(fruit['power']-skin['power'],30000)

 def test_boss_catalog_has_all_floors_and_distinct_rooftop_variants(self):
  rows=boss_catalog(self.store);self.assertEqual([r['id'] for r in rows if r['kind']=='tower'],list(range(1,3001)))
  self.assertEqual(sum(r['kind']=='map' for r in rows),72);self.assertEqual(sum(r['kind']=='challenge' for r in rows),40)
  regular=next(r for r in rows if r['kind']=='map' and r['id']==2462);gate=next(r for r in rows if r['kind']=='challenge' and r['id']==300035)
  self.assertEqual(regular['monsterIds'],[203801]);self.assertEqual(gate['monsterIds'],[2000033]);self.assertIn('->',gate['name']);self.assertNotEqual(regular['monsters'][0]['attrs'],gate['monsters'][0]['attrs'])
 def test_practice_lineup_is_owned_unique_and_separate(self):
  before=self.state();ids=[next(iter(before['generals'].values()))['generalId']]
  self.gm('bossPractice',json.dumps({'kind':'tower','id':3000,'generals':ids}));after=self.state()
  self.assertEqual([r['id'] for r in after['activeInstance']['data']['sprites'] if r['type']==1],ids)
  self.assertEqual(after.get('tower'),before.get('tower'));self.assertEqual(after['generals'],before['generals'])
  self.assertFalse(self.store.gm('pirate01','bossPractice',json.dumps({'kind':'tower','id':1,'generals':ids*2}))['ok'])
 def test_max_haki_and_stock_migration_are_capped_and_additive(self):
  before=self.state();s=deepcopy(before);s['settings']['testStockVersion']=4;s['inventory']['1013']=1;self.store._write('pirate01',s)
  topped=self.store.prepare_test_sandbox('pirate01');self.assertEqual(topped['inventory']['1013'],1000000000);self.assertTrue(all(topped['inventory'][str(i)]>=1000000 for i in range(1014,1021)))
  self.gm('maxHaki');after=self.state();self.assertEqual(len(after['suitStages']),35);self.assertTrue(all(r['stage']==15 for r in after['suitStages'].values()));self.assertEqual(after['inventory'],topped['inventory'])
  self.assertGreater(self.store.stats.evaluate(after)[next(iter(after['generals']))]['power'],self.store.stats.evaluate(topped)[next(iter(topped['generals']))]['power'])
  self.gm('maxHaki');self.assertEqual(self.state()['suitStages'],after['suitStages'])
 def test_max_ships_populates_native_protocol_replies(self):
  self.gm('maxShips');ships=self.store.command('pirate01',3401,{})['reply'];self.assertTrue(ships['ships']);self.assertTrue(all(r['lv']==10 for r in ships['ships']))
  info=self.store.command('pirate01',3400,{})['reply'];self.assertEqual(info['lv'],300);self.assertEqual(info['cabin'],300)
