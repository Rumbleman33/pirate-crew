import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('guide_catalog',Path(__file__).resolve().parents[1]/'tools/guide_catalog.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class GuideCatalogTests(unittest.TestCase):
    def test_packed_alignment_and_validation(self):
        self.assertEqual(module.decode_packed([2,'refId','hp',1,30]),[{'refId':'1','hp':'30'}])
        for bad in ([0], [2,'a','a',1,2], [2,'a','b',1]):
            with self.assertRaises(ValueError):module.decode_packed(bad)
    def test_real_icon_resolution_and_path_rejection(self):
        args=({'group':'7','name':'pet','type':'1'},{'7':{'group':'icon/item'}},{'1':{'type':'png'}})
        self.assertEqual(module.safe_icon(*args,{'icon/item/pet.png':'icon/item/pet.abcdef.png'}),'/game/icon/item/pet.abcdef.png')
        self.assertIsNone(module.safe_icon(*args,{'icon/item/pet.png':'https://wrong/p.png'}))
        self.assertIsNone(module.safe_icon(*args,{'icon/item/pet.png':'../secrets.png'}))
    def test_english_entity_level_join_and_missing_art(self):
        d=module.compile_catalog({'PetRef':[{'refId':'42','name':'original','english_name':'Bird','attrs':'1_3_0'}], 'Pet_All_Skill_Levels':[{'pet_id':'42','skill_level':'5','what_it_does':'Heal 15%'}]})
        p=d['systems']['pets'][0]
        self.assertEqual(p['name'],'Bird');self.assertIsNone(p['icon']);self.assertEqual(p['related'][0]['rows'][0]['skill_level'],'5');self.assertEqual(p['fields']['attrs'],'1_3_0')
    def test_progression_translation_keeps_level_identity(self):
        import tempfile,json,subprocess,sys
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);(p/'csv').mkdir();(p/'raw').mkdir()
            (p/'csv/PetRef.csv').write_text('refId,name\n42,Bird\n')
            (p/'csv/PetStageRef.csv').write_text('refId,order,attrs,attrs_english\n42,1,1_10_0,Attack +10\n42,2,1_20_0,Attack +20\n')
            (p/'raw/ref0.json').write_text(json.dumps({'PetStageRef':[3,'refId','order','attrs',42,1,'1_10_0',42,2,'1_20_0']}))
            subprocess.run([sys.executable,str(Path(module.__file__)),'--tables',str(p/'csv'),'--packed',str(p/'raw'),'--out',str(p/'out.json')],check=True,capture_output=True)
            rows=json.loads((p/'out.json').read_text())['systems']['pets'][0]['related'][0]['rows']
            self.assertEqual([r['attrs_english'] for r in rows],['Attack +10','Attack +20'])
if __name__=='__main__':unittest.main()
