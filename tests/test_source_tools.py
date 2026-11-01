import csv, importlib.util, json, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
TEST_TEMP=ROOT/'.local/unit-tests';TEST_TEMP.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('project',ROOT/'tools/project.py');project=importlib.util.module_from_spec(spec);spec.loader.exec_module(project)
sys.path.insert(0,str(ROOT/'engine'))
from offline_accounts import OfflineAccounts
from offline_stats import attributes,number
from offline_encounters import integer,finite

class PathAndDataTests(unittest.TestCase):
 def test_private_and_traversal_paths_rejected(self):
  for name in ['../accounts.json','data/../../x','/etc/passwd','C:/outside','data/runtime/x','runtime/accounts.json','x/TEST-LOGINS.txt','x/.env.production','data/saves/user.json']:
   self.assertFalse(project.safe_name(name),name)
  self.assertTrue(project.safe_name('data/tables/MonsterRef.csv'));self.assertTrue(project.safe_name('.env.example'))
 def fixture(self,root):
  rows={'MountStageRef':[{'refId':'1','startExp':'0','endExp':'0'}],'VoyageTitleRef':[{'refId':'1','maxLevel':'100','next':'0','attrs':''}],'GeneralRef':[{'refId':'1','type':'1','speed':'72'}],'MonsterRef':[{'refId':'10'}],'SceneRef':[{'refId':'100'},{'refId':'101'}],'TowerLevelRef':[{'refId':'1','monsterId':'10'}],'GeneralSkinRef':[{'skinId':'20','generalId':'1'}],'NpcRef':[{'refId':'30','type':'5','bossId':'10','sceneId':'100','data':'101'}]}
  for name,values in rows.items():
   with (root/(name+'.csv')).open('w',newline='',encoding='utf8') as f:
    writer=csv.DictWriter(f,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
 def test_validator_accepts_complete_synthetic_joins(self):
  with tempfile.TemporaryDirectory(dir=TEST_TEMP) as folder:
   root=Path(folder);self.fixture(root);self.assertEqual(len(project.validate(root)),8)
 def test_validator_rejects_missing_monster(self):
  with tempfile.TemporaryDirectory(dir=TEST_TEMP) as folder:
   root=Path(folder);self.fixture(root);(root/'TowerLevelRef.csv').write_text('refId,monsterId\n1,999\n',encoding='utf8')
   with self.assertRaisesRegex(ValueError,'missing monster'):project.validate(root)
 def test_validator_rejects_duplicate_skin_key(self):
  with tempfile.TemporaryDirectory(dir=TEST_TEMP) as folder:
   root=Path(folder);self.fixture(root);(root/'GeneralSkinRef.csv').write_text('skinId,generalId\n20,1\n20,1\n',encoding='utf8')
   with self.assertRaisesRegex(ValueError,'duplicate'):project.validate(root)
 def test_import_does_not_extract_captured_code_or_accounts(self):
  with tempfile.TemporaryDirectory(dir=TEST_TEMP) as folder:
   root=Path(folder);source=root/'source';source.mkdir();(source/'game').mkdir();(source/'game/dummy.txt').write_text('media placeholder')
   with zipfile.ZipFile(source/'simulation.zip','w') as z:
    z.writestr('offline_core.py','UNTRUSTED MODULE');z.writestr('runtime/accounts.json','PRIVATE RECORD');z.writestr('data/catalog.json','{}')
   target=root/'checkout';target.mkdir()
   with patch.object(project,'ROOT',target),patch.object(project,'ASSETS',target/'.local/assets'),patch.object(project,'validate'):
    project.import_pack(source)
   self.assertFalse((target/'engine/offline_core.py').exists());self.assertFalse((target/'engine/runtime/accounts.json').exists());self.assertTrue((target/'engine/data/catalog.json').exists())
 def test_import_rejects_traversal_before_writing(self):
  with tempfile.TemporaryDirectory(dir=TEST_TEMP) as folder:
   source=Path(folder)
   with zipfile.ZipFile(source/'simulation.zip','w') as z:z.writestr('data/../../escaped.txt','bad')
   with self.assertRaisesRegex(ValueError,'Unsafe'):project.import_pack(source)
 def test_import_rejects_private_files_inside_data(self):
  with tempfile.TemporaryDirectory(dir=TEST_TEMP) as folder:
   source=Path(folder)
   with zipfile.ZipFile(source/'simulation.zip','w') as z:z.writestr('data/accounts.json','private')
   with self.assertRaisesRegex(ValueError,'Unsafe'):project.import_pack(source)

class FreshAccountTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(dir=TEST_TEMP);cls.root=Path(cls.tmp.name);cls.accounts=OfflineAccounts(cls.root)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def credentials(self):
  import re
  return dict(re.findall(r'^(pirate\d{2})\s+(\S+)$',(self.root/'TEST-LOGINS.txt').read_text(encoding='utf8'),re.M))
 def test_fresh_accounts_are_salted_not_plaintext(self):
  passwords=self.credentials();raw=(self.root/'runtime/accounts.json').read_text();records=json.loads(raw)['users'];self.assertEqual(len(passwords),10)
  self.assertEqual(len({r['salt'] for r in records.values()}),10)
  self.assertTrue(all(password not in raw for password in passwords.values()))
 def test_public_profile_contains_no_verifier(self):
  row=self.accounts.public_account('pirate01');self.assertNotIn('passwordHash',row);self.assertNotIn('salt',row)
 def test_login_session_reloads_and_logout_revokes(self):
  login=self.accounts.login('pirate02',self.credentials()['pirate02']);token=login['token'];reloaded=OfflineAccounts(self.root)
  self.assertEqual(reloaded.account_for_token(token),'pirate02');reloaded.logout(token);self.assertIsNone(reloaded.account_for_token(token))
 def test_wrong_password_and_unknown_account_are_rejected(self):
  self.assertIsNone(self.accounts.login('pirate01','not-the-generated-password'));self.assertIsNone(self.accounts.login('unknown','anything'))
 def test_tokens_are_hashed_on_disk(self):
  token=self.accounts.login('pirate03',self.credentials()['pirate03'])['token'];self.assertNotIn(token,(self.root/'runtime/sessions.json').read_text())

class NumericBoundaryTests(unittest.TestCase):
 def test_nonfinite_input_is_not_a_stat(self):
  self.assertEqual(number('nan'),0);self.assertEqual(finite('inf'),0);self.assertEqual(integer('bad',7),7)
 def test_attribute_parser_preserves_duplicate_additions(self):
  self.assertEqual(attributes('1_10#1_5#2_100'),{1:15,2:100})

if __name__=='__main__':unittest.main()
