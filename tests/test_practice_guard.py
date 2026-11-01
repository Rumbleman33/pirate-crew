"""Practice transitions preserve unrelated encounters and their accounting."""
import copy, json, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from offline_core import SimulationError
from offline_encounters import OfflineEncounters
from offline_testing import apply

class PracticeGuardTests(unittest.TestCase):
 def setUp(self):
  def fail(code,message):raise SimulationError(code,message)
  self.store=SimpleNamespace(systems=SimpleNamespace(fail=fail),progression=SimpleNamespace(crew_capacity=lambda state:3),_general=lambda state,gid:state['generals'][str(gid)])
  self.store.encounters=OfflineEncounters.__new__(OfflineEncounters)
  self.state={'settings':{},'generals':{'1':{'generalId':1,'isSelect':True}},'inventory':{'102':500},'bounty':{'occupied':True},'towerFloor':1}
  self.boss=patch('offline_testing.boss_catalog',return_value=[{'kind':'tower','id':1,'name':'Synthetic boss','monsterIds':[10]}]);self.boss.start();self.addCleanup(self.boss.stop)
  self.make=patch.object(self.store.encounters,'_make',side_effect=self.make_active);self.mock_make=self.make.start();self.addCleanup(self.make.stop)
 def make_active(self,state,*args,**kwargs):
  active={'kind':'practice','data':{'uid':42,'refId':201,'lv':1},'settled':False,'left':False};state['activeInstance']=active;return active
 def practice(self):return apply(self.store,self.state,'bossPractice',json.dumps({'kind':'tower','id':1,'generals':[1]}))
 def test_every_active_encounter_is_rejected_without_any_state_change(self):
  for kind in ('tower','bounty','map','challenge','practice'):
   self.state['activeInstance']={'kind':kind,'data':{'uid':17,'refId':201,'lv':1},'practice':kind=='practice','settled':False,'left':False}
   before=copy.deepcopy(self.state)
   with self.subTest(kind=kind),self.assertRaises(SimulationError) as caught:self.practice()
   self.assertEqual(caught.exception.code,'ACTIVE_ENCOUNTER');self.assertEqual(self.state,before)
  self.mock_make.assert_not_called()
 def test_settled_and_left_encounters_are_archived_before_replacement(self):
  for flag in ('settled','left'):
   previous={'kind':'tower','data':{'uid':17,'refId':201,'lv':1},flag:True}
   self.state['activeInstance']=copy.deepcopy(previous)
   inventory=copy.deepcopy(self.state['inventory']);bounty=copy.deepcopy(self.state['bounty'])
   self.practice()
   self.assertIn(previous,self.state['encounterHistory']);self.assertEqual(self.state['inventory'],inventory);self.assertEqual(self.state['bounty'],bounty)
 def test_manual_close_then_reopen_survives_serialization(self):
  self.practice();apply(self.store,self.state,'endBossPractice','42')
  self.assertNotIn('activeInstance',self.state);self.assertTrue(self.state['encounterHistory'][-1]['left'])
  self.state=json.loads(json.dumps(self.state));self.practice();self.assertTrue(self.state['activeInstance']['practice'])
  self.assertEqual(self.state['inventory']['102'],500);self.assertEqual(self.state['towerFloor'],1)
 def test_defeated_practice_can_be_reopened_without_rewards(self):
  self.practice();self.state['activeInstance'].update(settled=True,result='defeat')
  self.practice();self.assertEqual(self.state['encounterHistory'][-1]['result'],'defeat')
  self.assertEqual(self.state['inventory']['102'],500)
 def test_invalid_selection_does_not_archive_completed_encounter(self):
  self.state['activeInstance']={'kind':'tower','data':{'uid':17},'settled':True}
  before=copy.deepcopy(self.state)
  with patch('offline_testing.boss_catalog',return_value=[]),self.assertRaises(SimulationError):self.practice()
  self.assertEqual(before,self.state)
