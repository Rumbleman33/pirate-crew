"""Startup dependencies are checked against synthetic tables before acceptance."""
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import test_source_tools as fixtures
project=fixtures.project

class StartupValidationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.data=Path(self.tmp.name);self.tables=self.data/'tables';self.tables.mkdir()
  fixtures.PathAndDataTests().fixture(self.tables)
 def test_each_unconditional_dependency_must_be_nonempty(self):
  for name in ('GeneralRef','MonsterRef','SceneRef','TowerLevelRef','MountStageRef','VoyageTitleRef'):
   p=self.tables/(name+'.csv');original=p.read_bytes()
   for replacement in (None,original.split(b'\n')[0]+b'\n'):
    if replacement is None:p.unlink()
    else:p.write_bytes(replacement)
    with self.subTest(table=name,replacement=replacement),self.assertRaisesRegex(ValueError,name):project.validate(self.tables)
   p.write_bytes(original)
 def test_missing_startup_columns_name_table_and_field(self):
  for name,column in (('GeneralRef','speed'),('MountStageRef','startExp'),('VoyageTitleRef','maxLevel')):
   p=self.tables/(name+'.csv');original=p.read_bytes()
   import csv,io
   rows=list(csv.DictReader(io.StringIO(original.decode())))
   with p.open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=[c for c in rows[0] if c!=column]);writer.writeheader();writer.writerows([{k:v for k,v in r.items() if k!=column} for r in rows])
   with self.assertRaisesRegex(ValueError,name+'.csv: missing '+column):project.validate(self.tables)
   p.write_bytes(original)
 def test_initial_voyage_title_and_numeric_fields_are_required(self):
  p=self.tables/'VoyageTitleRef.csv';p.write_text('refId,maxLevel,next,attrs\n2,100,0,\n')
  with self.assertRaisesRegex(ValueError,'initial title'):project.validate(self.tables)
  p.write_text('refId,maxLevel,next,attrs\n1,nan,0,\n')
  with self.assertRaisesRegex(ValueError,'invalid integer maxLevel'):project.validate(self.tables)
 def test_smoke_catches_other_invalid_present_tables_without_creating_active_saves(self):
  (self.tables/'PetStageRef.csv').write_text('refId,order\n1,broken\n')
  with self.assertRaisesRegex(ValueError,'Captain startup/load failed'):project.validate(self.tables)
  self.assertFalse((self.data/'runtime').exists())
 def test_protocol_metadata_is_validated_separately(self):
  with self.assertRaisesRegex(ValueError,'metadata'):project.validate_metadata(self.data)
  (self.data/'catalog.json').write_text(json.dumps({'commands':[{'id':1001}],'initCommandIds':[1001]}))
  (self.data/'schemas.json').write_text(json.dumps({'SyntheticReply':{'fields':[]}}))
  project.validate_metadata(self.data)
  (self.data/'catalog.json').write_text(json.dumps({'commands':[{'id':1001}],'initCommandIds':[9999]}))
  with self.assertRaisesRegex(ValueError,'initialization'):project.validate_metadata(self.data)
