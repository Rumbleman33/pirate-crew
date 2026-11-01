import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import test_tester_fixes as fixture

class VoyageStockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixture.TesterRegressionTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):
        s=self.store.reset('pirate01');s['settings']['autoVoyageObjectives']=False;self.store._write('pirate01',s)
    def cmd(self,cid,**p):return self.store.command('pirate01',cid,p)
    def good(self,r):self.assertTrue(r['ok'],r.get('error'));return r['reply']
    def test_every_gear_variant_preloaded_three_times_once(self):
        s=self.store.prepare_test_sandbox('pirate01');counts={}
        for e in s['equipment']:counts[e['equipRefId']]=counts.get(e['equipRefId'],0)+1
        self.assertEqual(len(counts),len(self.store.equips));self.assertTrue(all(n>=3 for n in counts.values()))
        self.assertEqual(len({e['equipId'] for e in s['equipment']}),len(s['equipment']))
        self.assertGreaterEqual(s['inventory']['109'],2550)
        self.assertEqual(len(self.store.prepare_test_sandbox('pirate01')['equipment']),len(s['equipment']))
        capacity=self.good(self.cmd(1112,type=[2]))['capacities'][0]
        self.assertGreaterEqual(capacity['max'],10000);self.assertEqual(capacity['cur'],len(s['equipment']))
        self.assertEqual(s['progression'].get('gearForged',0),0)
    def test_voyage_claims_then_promotes_with_gift_and_next_tasks(self):
        before=self.good(self.cmd(2100));self.assertEqual(before['title'],1)
        self.assertFalse(self.cmd(2101)['ok'])
        self.store.gm('pirate01','completeVoyageTasks','')
        tasks=self.good(self.cmd(2100))['tasks'];self.assertTrue(all(t['state']==2 for t in tasks))
        self.assertFalse(self.cmd(2101)['ok'])
        for task in tasks:self.good(self.cmd(2102,taskRefId=task['refId']))
        promoted=self.good(self.cmd(2101));self.assertEqual(promoted['title'],2)
        self.assertTrue(promoted['reward']);self.assertTrue(all(t['refId'] not in {r['refId'] for r in tasks} for t in promoted['tasks']))
        self.assertFalse(self.cmd(2102,taskRefId=tasks[0]['refId'])['ok'])
    def test_player_exp_respects_one_piece_cap_then_new_cap(self):
        s=self.store.snapshot('pirate01');s['inventory']['106']=10**12;self.store._advance_player_level(s)
        self.assertEqual(s['player']['level'],30);self.store._write('pirate01',s)
        self.assertFalse(self.cmd(1009)['ok'])
        self.store.gm('pirate01','completeVoyageTasks','')
        for t in self.good(self.cmd(2100))['tasks']:self.good(self.cmd(2102,taskRefId=t['refId']))
        self.good(self.cmd(2101));self.assertEqual(self.good(self.cmd(1009))['newLevel'],31)
    def test_voyage_objectives_read_actual_state(self):
        s=self.store.snapshot('pirate01');s['player']['level']=30;s['towerFloor']=11
        for gid in list(self.store.generals)[:5]:s['generals'][str(gid)]=self.store._general_vo(gid,10,0)
        boss=next(k for k,r in self.store.monsters.items() if int(r.get('type',0))==3)
        s['progression']['kills'][str(boss)]=5;self.store._write('pirate01',s)
        self.assertTrue(all(t['state']==2 for t in self.good(self.cmd(2100))['tasks']))
