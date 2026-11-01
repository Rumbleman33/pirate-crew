"""Failed imports preserve the previous pack; fixtures contain synthetic data only."""
import importlib.util, json, os, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('transaction_project',ROOT/'tools/project.py')
project=importlib.util.module_from_spec(spec);spec.loader.exec_module(project)

class ImportTransactionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)/'checkout';self.root.mkdir();self.source=Path(self.tmp.name)/'source';self.source.mkdir()
  for name in ('engine/data/tables/GeneralRef.csv','engine/public/old.json','.local/assets/game/obsolete.txt','.local/import-manifest.json','engine/runtime/saves/keep.json'):
   p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('previous '+name)
  self.before=self.snapshot()
  self.pack()
  self.patches=[patch.object(project,'ROOT',self.root),patch.object(project,'ASSETS',self.root/'.local/assets')]
  for p in self.patches:p.start();self.addCleanup(p.stop)
 def snapshot(self):
  return {p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
 def pack(self,invalid=False):
  with zipfile.ZipFile(self.source/'simulation.zip','w') as z:
   for name,data in {'MountStageRef':'refId,startExp,endExp\n1,0,0\n','VoyageTitleRef':'refId,maxLevel,next,attrs\n1,100,0,\n','GeneralRef':'refId,type,speed\n999,1,72\n','MonsterRef':'refId\n10\n','SceneRef':'refId\n100\n','TowerLevelRef':'refId,monsterId\n1,10\n'}.items():
    if invalid and name!='GeneralRef':continue
    z.writestr('data/tables/'+name+'.csv',data)
  (self.source/'game').mkdir(exist_ok=True);(self.source/'game/new.txt').write_text('new media')
 def test_missing_table_leaves_every_previous_byte_unchanged(self):
  self.pack(invalid=True)
  with self.assertRaisesRegex(ValueError,'Required table'):project.import_pack(self.source)
  self.assertEqual(self.snapshot(),self.before)
 def test_malformed_csv_leaves_every_previous_byte_unchanged(self):
  with zipfile.ZipFile(self.source/'simulation.zip','a') as z:z.writestr('data/tables/Broken.csv','x,y\n1,2,3\n')
  with self.assertRaisesRegex(ValueError,'malformed'):project.import_pack(self.source)
  self.assertEqual(self.snapshot(),self.before)
 def test_corrupt_archive_and_copy_failure_preserve_previous_pack(self):
  (self.source/'simulation.zip').write_bytes(b'broken')
  with self.assertRaises(zipfile.BadZipFile):project.import_pack(self.source)
  self.assertEqual(self.snapshot(),self.before);self.pack()
  with patch.object(project.shutil,'copy2',side_effect=OSError('copy failed')):
   with self.assertRaisesRegex(OSError,'copy failed'):project.import_pack(self.source)
  self.assertEqual(self.snapshot(),self.before)
 def test_promotion_failure_rolls_back_each_previous_tree_and_manifest(self):
  replace=os.replace
  for fail_at in range(1,9):
   count=0
   def failing(source,target):
    nonlocal count
    if self.root in Path(target).parents:count+=1
    if self.root in Path(target).parents and count==fail_at:raise OSError('rename failed')
    return replace(source,target)
   with self.subTest(fail_at=fail_at),patch.object(project.os,'replace',side_effect=failing):
    with self.assertRaisesRegex(OSError,'rename failed'):project.import_pack(self.source)
   self.assertEqual(self.snapshot(),self.before)
 def test_success_replaces_obsolete_files_and_preserves_source_and_saves(self):
  project.import_pack(self.source)
  self.assertFalse((self.root/'.local/assets/game/obsolete.txt').exists())
  self.assertFalse((self.root/'engine/public/old.json').exists())
  self.assertEqual((self.root/'engine/runtime/saves/keep.json').read_bytes(),self.before['engine/runtime/saves/keep.json'])
  self.assertEqual((self.root/'engine/data/tables/GeneralRef.csv').read_text(),'refId,type,speed\n999,1,72\n')
  manifest=json.loads((self.root/'.local/import-manifest.json').read_text())
  self.assertEqual(len(manifest['files']),7)
 def test_rollback_failure_keeps_recovery_copies(self):
  replace=os.replace;count=0
  def failing(source,target):
   nonlocal count
   if self.root in Path(target).parents:count+=1
   if self.root in Path(target).parents and count in (4,5):raise OSError('disk failed')
   return replace(source,target)
  with patch.object(project.os,'replace',side_effect=failing):
   with self.assertRaisesRegex(project.ImportRecoveryError,'retained'):project.import_pack(self.source)
  stages=list(self.root.glob('.import-*'));self.assertEqual(len(stages),1)
  self.assertEqual((stages[0]/'previous-0/tables/GeneralRef.csv').read_bytes(),self.before['engine/data/tables/GeneralRef.csv'])
