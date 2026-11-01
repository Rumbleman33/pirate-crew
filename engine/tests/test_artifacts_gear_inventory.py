import unittest,json,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
import test_tester_fixes as fixture

class ArtifactGearInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixture.TesterRegressionTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):self.store.reset('pirate01');self.store.prepare_test_sandbox('pirate01')
    def cmd(self,cid,**p):return self.store.command('pirate01',cid,p)
    def good(self,r):self.assertTrue(r['ok'],r.get('error'));return r['reply']
    def prep(self):
        s=self.store.snapshot('pirate01');s['generals']['2000004']=self.store._general_vo(2000004,115,0)
        for g in s['generals'].values():g['level']=115
        self.store._write('pirate01',s);return s
    def test_artifact_activate_upgrade_cap_cost_entries(self):
        self.prep();before=self.store.snapshot('pirate01')['inventory']['4001']
        self.assertEqual(self.good(self.cmd(3501,refId=1))['info']['lv'],1)
        self.assertEqual(self.good(self.cmd(3502,refId=1))['info']['lv'],2)
        self.assertEqual(self.store.snapshot('pirate01')['inventory']['4001'],before-3)
        for _ in range(3):self.good(self.cmd(3502,refId=1))
        before=self.store.snapshot('pirate01');failed=self.cmd(3502,refId=1)
        self.assertEqual(failed['error']['code'],'MAX_ARTIFACT_LEVEL')
        self.assertEqual(before['inventory'],self.store.snapshot('pirate01')['inventory'])
        g=next(g for g in self.store._roster(before) if g['generalId']==2000004)
        self.assertEqual(len([e for e in g['entryInfos'] if 31000011<=e['refId']<=31000015]),5)
        self.assertEqual(self.good(self.cmd(3500))['infos'][0]['lv'],5)
    def test_gear_mixed_ids_replace_move_unequip_and_power(self):
        s=self.prep();gid=2000001;typ=int(self.store.generals[gid]['type'])
        row=next(r for r in self.store.equips.values() if int(r['generalType'])==typ and int(r['needLevel'])<=115)
        self.store.gm('pirate01','addEquip',f"{row['refId']}_2")
        gear=self.store.snapshot('pirate01')['equipment'][-2:]
        self.good(self.cmd(1351,generalId=gid,equipId=str(gear[0]['equipId'])))
        reply=self.good(self.cmd(1351,generalId=gid,equipId=gear[1]['equipId']))
        self.assertEqual(len(reply['equips']),2)
        self.assertEqual(sum(e['generalId']==gid for e in self.store.snapshot('pirate01')['equipment']),1)
        before=self.store.stats.evaluate(self.store.snapshot('pirate01'))[str(gid)]['power']
        self.good(self.cmd(1352,equipId=str(gear[1]['equipId'])))
        after=self.store.stats.evaluate(self.store.snapshot('pirate01'))[str(gid)]['power']
        self.assertGreater(before,after)
    def test_gear_class_level_lock_salvage_atomicity(self):
        s=self.store.snapshot('pirate01');e=s['equipment'][0]
        self.assertFalse(self.cmd(1351,generalId=2000001,equipId=e['equipId'])['ok'])
        self.good(self.cmd(1355,equipId=str(e['equipId'])))
        before=self.store.snapshot('pirate01')
        self.assertFalse(self.cmd(1354,equipIds=[str(e['equipId'])])['ok'])
        self.assertEqual(before['equipment'],self.store.snapshot('pirate01')['equipment'])
        self.good(self.cmd(1355,equipId=e['equipId']));self.good(self.cmd(1354,equipIds=[str(e['equipId'])]))
    def test_choice_box_validates_before_spending(self):
        before=self.store.snapshot('pirate01');rid=1030
        failed=self.cmd(1101,refId=rid,useCount=1,extParams='102_1')
        self.assertFalse(failed['ok']);self.assertEqual(before['inventory'],self.store.snapshot('pirate01')['inventory'])
        r=self.good(self.cmd(1101,refId=rid,useCount=2,extParams='2000002_2#2000005_0'))
        self.assertEqual(r['rewards'][0]['refId'],2000002);self.assertEqual(r['rewards'][0]['count'],2)
        after=self.store.snapshot('pirate01');self.assertEqual(after['inventory'][str(rid)],before['inventory'][str(rid)]-2)
    def test_random_box_and_zero_quantity(self):
        before=self.store.snapshot('pirate01')
        self.assertFalse(self.cmd(1101,refId=1033,useCount=0)['ok'])
        self.assertEqual(before['inventory'],self.store.snapshot('pirate01')['inventory'])
        with patch('offline_equipment.secrets.randbelow',return_value=0):r=self.good(self.cmd(1101,refId=1033,useCount=1))
        self.assertTrue(r['rewards'])
    def test_exp_consumable_advances_level(self):
        before=self.store.snapshot('pirate01')['player']['level']
        self.good(self.cmd(1101,refId=1042,useCount=10))
        self.assertGreater(self.store.snapshot('pirate01')['player']['level'],before)
