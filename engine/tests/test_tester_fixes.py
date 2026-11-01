import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from offline_core import OfflineStore
from offline_accounts import OfflineAccounts


class TesterRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work=PROJECT.parent/'.local/test-work/tester-fixes'
        cls.work.mkdir(parents=True,exist_ok=True)
        cls.tmp=tempfile.TemporaryDirectory(prefix='tester-fixes-',dir=cls.work)
        cls.root=Path(cls.tmp.name)
        (cls.root/'runtime').mkdir()
        OfflineAccounts(cls.root)
        cls.store=OfflineStore(cls.root,PROJECT/'data/tables')
        cls.store.catalog=json.loads((PROJECT/'data/catalog.json').read_text())
        cls.store.schemas=json.loads((PROJECT/'data/schemas.json').read_text())
        cls.store.commands={r['id']:r for r in cls.store.catalog['commands']}
        cls.store.init_ids=set(cls.store.catalog['initCommandIds'])

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def setUp(self):self.store.reset('pirate01')
    def cmd(self,cid,**payload):return self.store.command('pirate01',cid,payload)
    def stock(self):return self.store.prepare_test_sandbox('pirate01')
    def good(self,result):self.assertTrue(result['ok'],result.get('error'));return result['reply']

    def test_stock_is_additive_once_and_does_not_upgrade(self):
        before=self.store.snapshot('pirate01');after=self.stock()
        self.assertEqual(before['generals'],after['generals'])
        self.assertEqual(after['mounts'],[]);self.assertEqual(after['pets'],[])
        for rid in [3000001,4000001,4001,10000001,15000001,1009]:self.assertGreaterEqual(after['inventory'][str(rid)],9999)
        self.assertEqual(after['inventory'].get('106',0),before['inventory'].get('106',0))
        self.store.gm('pirate01','subItem','1_3000001_1')
        self.assertEqual(self.stock()['inventory']['3000001'],after['inventory']['3000001']-1)
        self.store.gm('pirate01','stockTestItems','')
        self.assertEqual(self.stock()['inventory']['3000001'],after['inventory']['3000001'])

    def test_pet_cap_keeps_power_and_inventory_unchanged(self):
        self.stock();rid=4000001
        rows=[r for r in self.store.table('PetStageRef') if int(r['refId'])==rid]
        for _ in rows:self.good(self.cmd(2601,refId=rid))
        before=self.store.snapshot('pirate01');failed=self.cmd(2601,refId=rid)
        self.assertEqual(failed['error']['code'],'MAX_PET_STAGE')
        after=self.store.snapshot('pirate01')
        self.assertEqual(before['inventory'],after['inventory']);self.assertEqual(before['player']['attrs'],after['player']['attrs'])

    def test_mount_cap_and_reference_costs(self):
        self.stock();rid=3000001;self.good(self.cmd(2701,refId=rid))
        rows=[r for r in self.store.table('MountStarRef') if int(r['refId'])==rid]
        for _ in rows[1:]:self.good(self.cmd(2703,refId=rid))
        before=self.store.snapshot('pirate01');result=self.cmd(2703,refId=rid)
        self.assertEqual(result['error']['code'],'MAX_MOUNT_STAR')
        self.assertEqual(before['inventory'],self.store.snapshot('pirate01')['inventory'])
        before=self.store.snapshot('pirate01');self.good(self.cmd(2702,refId=rid));after=self.store.snapshot('pirate01')
        self.assertLess(after['inventory']['1009'],before['inventory']['1009'])
        self.assertGreater(after['player']['attrs'][-1]['attrValue'],0)

    def test_mount_assignment_replaces_previous_and_returns_both(self):
        self.stock()
        for rid in [3000001,3000002]:self.good(self.cmd(2701,refId=rid))
        gid=int(next(iter(self.store.snapshot('pirate01')['generals'])))
        self.good(self.cmd(2706,refId=3000001,generalId=gid))
        reply=self.good(self.cmd(2706,refId=3000002,generalId=gid))
        self.assertEqual(len(reply['mounts']),2)
        self.assertEqual(sum(m['generalId']==gid for m in self.store.snapshot('pirate01')['mounts']),1)
        self.good(self.cmd(2709,generalId=gid));self.good(self.cmd(2707,generalId=gid))
        self.assertFalse(any(m['generalId']==gid for m in self.store.snapshot('pirate01')['mounts']))

    def test_old_overcap_save_is_repaired_and_persisted(self):
        s=self.store.snapshot('pirate01');gid=int(next(iter(s['generals'])))
        s['pets']=[{'refId':4000001,'stage':99}]
        s['mounts']=[{'refId':rid,'star':99,'level':99999,'generalId':gid,'use':True} for rid in [3000001,3000002]]
        self.store._write('pirate01',s)
        repaired=self.store.snapshot('pirate01')
        self.assertEqual(repaired['pets'][0]['stage'],10)
        self.assertTrue(all(m['star']==10 for m in repaired['mounts']))
        self.assertEqual(sum(m['generalId']==gid for m in repaired['mounts']),1)
        self.assertEqual(repaired['mounts'],json.loads(self.store._path('pirate01').read_text())['mounts'])
        self.assertGreater(repaired['player']['attrs'][-1]['attrValue'],0)

    def test_appearance_and_skill_removal_are_different_commands(self):
        self.stock();self.good(self.cmd(2601,refId=4000001))
        self.good(self.cmd(2602))
        self.good(self.cmd(2606,refId=4000001));self.good(self.cmd(2604,index=1,skillId=401))
        self.good(self.cmd(2605,index=1))
        reply=self.good(self.cmd(2600))
        self.assertEqual(reply['appearId'],4000001);self.assertEqual(reply['petSkills'],[])

    def test_artifact_craft_spends_materials_and_reports_results(self):
        self.stock();before=self.store.snapshot('pirate01')
        with patch('offline_workshop.secrets.randbelow',return_value=0):reply=self.good(self.cmd(1357,refId=1,count=1))
        self.assertEqual(reply['rewards'][0]['refId'],4001)
        after=self.store.snapshot('pirate01')
        self.assertEqual(after['inventory']['4001'],before['inventory']['4001']+1)
        self.assertEqual(after['inventory']['15000001'],before['inventory']['15000001']-1)
        self.assertFalse(self.cmd(1357,refId=1,count=0)['ok'])

    def test_workshop_initializes_valid_refs_and_forges_equipment(self):
        self.stock();info=self.good(self.cmd(1750))['info']
        self.assertEqual(info['level'],10);self.assertEqual(info['round'],1)
        result=self.cmd(1751,itemId=1002,count=2);reply=self.good(result)
        self.assertEqual(len(reply['equips']),2)
        self.assertEqual(len({e['equipId'] for e in reply['equips']}),2)
        self.assertTrue(any(b['id']==1353 for b in result['broadcasts']))
        self.assertFalse(self.cmd(1752,level=0)['ok'])
