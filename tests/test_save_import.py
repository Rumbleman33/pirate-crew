"""Save-import regressions using synthetic tables and disposable captains only."""
import copy
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
from offline_core import OfflineStore, SimulationError


class SaveImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = ROOT / '.local' / 'unit-tests'
        work.mkdir(parents=True, exist_ok=True)
        cls.tmp = tempfile.TemporaryDirectory(dir=work)
        cls.root = Path(cls.tmp.name)
        tables = cls.root / 'data' / 'tables'
        tables.mkdir(parents=True)
        fixtures = {
            'GeneralRef': [{'refId': 1, 'type': 1, 'speed': 72}],
            'MountStageRef': [{'refId': 1, 'startExp': 0, 'endExp': 0}],
            'VoyageTitleRef': [{'refId': 1, 'maxLevel': 100, 'next': 0, 'attrs': ''}],
        }
        for name, rows in fixtures.items():
            with (tables / (name + '.csv')).open('w', newline='', encoding='utf8') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        cls.store = OfflineStore(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        for username in ('pirate01', 'pirate02'):
            self.store.reset(username)
            self.store.snapshot(username)
        self.document = self.store.export_save('pirate01')
        self.original = self.store._path('pirate01').read_bytes()
        self.other = self.store._path('pirate02').read_bytes()
        self.backups = set((self.store.runtime / 'backups').glob('*'))

    def assert_rejected(self, document):
        with self.assertRaises(SimulationError) as caught:
            self.store.import_save('pirate01', document)
        self.assertEqual(caught.exception.code, 'INVALID_SAVE')
        self.assertEqual(self.store._path('pirate01').read_bytes(), self.original)
        self.assertEqual(self.store._path('pirate02').read_bytes(), self.other)
        self.assertEqual(set((self.store.runtime / 'backups').glob('*')), self.backups)

    def test_bad_scene_is_rejected_without_replacing_current_save(self):
        self.document['state']['scene'] = None
        self.assert_rejected(self.document)
        self.assertIsInstance(self.store.snapshot('pirate01')['scene'], dict)

    def test_invalid_envelopes_and_versions_are_rejected(self):
        for document in (None, [], 'not a save', {'format': 'other', 'version': 1, 'state': self.document['state']},
                         {**self.document, 'version': 2}, {**self.document, 'version': True},
                         {**self.document, 'state': None}):
            with self.subTest(document_type=type(document).__name__):
                self.assert_rejected(document)
        for key, version in (('schemaVersion', 2), ('saveSchemaVersion', 15)):
            document = copy.deepcopy(self.document)
            document['state'][key] = version
            self.assert_rejected(document)

    def test_malformed_containers_and_roster_are_rejected(self):
        for key, value in (('settings', []), ('player', None), ('equipment', {}), ('tasks', [None]),
                           ('generals', {'1': None}), ('pets', [None]), ('shipyard', [])):
            document = copy.deepcopy(self.document)
            document['state'][key] = value
            with self.subTest(key=key):
                self.assert_rejected(document)

    def test_invalid_nested_state_is_rejected_before_any_backup(self):
        for change in ('missing_map', 'bad_personality', 'unknown_general'):
            document = copy.deepcopy(self.document)
            if change == 'missing_map':
                del document['state']['scene']['mapId']
            elif change == 'bad_personality':
                document['state']['player']['personality'] = []
            else:
                document['state']['generals']['1']['generalId'] = 999
            with self.subTest(change=change):
                self.assert_rejected(document)

    def test_invalid_inventory_numbers_and_nonfinite_json_are_rejected(self):
        for count in (-1, 1.5, True, float('nan'), float('inf'), 10**13):
            document = copy.deepcopy(self.document)
            document['state']['inventory']['102'] = count
            with self.subTest(count=count):
                self.assert_rejected(document)
        document = copy.deepcopy(self.document)
        document['state']['scene']['moveSpeed'] = float('nan')
        self.assert_rejected(document)

    def test_valid_round_trip_preserves_progress_and_local_identity(self):
        document = copy.deepcopy(self.document)
        document['state']['inventory']['102'] = 456
        document['state']['settings']['customSaveMarker'] = 'retained'
        result = self.store.import_save('pirate02', document)
        reloaded = self.store.snapshot('pirate02')
        self.assertEqual(reloaded['inventory']['102'], 456)
        self.assertEqual(reloaded['settings']['customSaveMarker'], 'retained')
        self.assertEqual(result['username'], 'pirate02')
        self.assertEqual(reloaded['playerId'], self.store.accounts.public_account('pirate02')['playerId'])
        self.assertEqual(reloaded['player']['playerId'], reloaded['playerId'])
        self.assertEqual(self.store._path('pirate01').read_bytes(), self.original)

    def test_legacy_raw_save_is_migrated_before_commit(self):
        raw = copy.deepcopy(self.document['state'])
        raw.pop('saveSchemaVersion', None)
        raw.pop('generalSkins', None)
        self.store.import_save('pirate01', raw)
        self.assertEqual(self.store.snapshot('pirate01')['saveSchemaVersion'], 14)
        self.assertIn('generalSkins', self.store.snapshot('pirate01'))

    def test_missing_persistent_core_fields_are_rejected(self):
        for key in ('mail', 'shopPurchases', 'instanceLevels', 'clientActions'):
            document = copy.deepcopy(self.document)
            document['state'].pop(key)
            with self.subTest(key=key):
                self.assert_rejected(document)

    def test_regular_read_still_creates_legacy_migration_backup(self):
        state = copy.deepcopy(self.document['state'])
        state['saveSchemaVersion'] = 13
        self.store._write('pirate01', state)
        backup = self.store.runtime / 'backups' / 'pirate01-before-v14.json'
        backup.unlink(missing_ok=True)
        original = self.store._path('pirate01').read_bytes()
        self.assertEqual(self.store.snapshot('pirate01')['saveSchemaVersion'], 14)
        self.assertEqual(backup.read_bytes(), original)

    def test_import_revision_advances_past_the_current_save(self):
        state = copy.deepcopy(self.document['state'])
        state['updatedAt'] = 10**15
        self.store._write('pirate01', state)
        before = self.store.snapshot('pirate01')['updatedAt']
        untouched = copy.deepcopy(self.document)
        result = self.store.import_save('pirate01', self.document)
        self.assertGreater(result['updatedAt'], before)
        self.assertEqual(self.document, untouched)

    def test_backup_contains_previous_bytes_and_can_restore_them(self):
        self.document['state']['inventory']['102'] = 456
        self.store.import_save('pirate01', self.document)
        new = set((self.store.runtime / 'backups').glob('*')) - self.backups
        self.assertEqual(len(new), 1)
        backup = new.pop()
        self.assertEqual(backup.read_bytes(), self.original)
        self.store.import_save('pirate01', json.loads(backup.read_text()))
        self.assertEqual(self.store.snapshot('pirate01')['inventory']['102'], 1000000)

    def test_valid_import_can_recover_a_corrupt_existing_save(self):
        self.store._path('pirate01').write_bytes(b'{broken JSON')
        self.store.import_save('pirate01', self.document)
        new = set((self.store.runtime / 'backups').glob('*')) - self.backups
        self.assertEqual(len(new), 1)
        self.assertEqual(new.pop().read_bytes(), b'{broken JSON')
        self.assertEqual(self.store.snapshot('pirate01')['mode'], 'offline')

    def test_backup_failure_leaves_current_save_untouched(self):
        with patch('offline_core.tempfile.NamedTemporaryFile', side_effect=OSError('synthetic disk failure')):
            with self.assertRaises(OSError):
                self.store.import_save('pirate01', self.document)
        self.assertEqual(self.store._path('pirate01').read_bytes(), self.original)

    def test_replacement_failure_keeps_current_save_and_recoverable_backup(self):
        import os
        replace = os.replace
        def fail_current(source, target):
            if Path(target) == self.store._path('pirate01'):
                raise OSError('synthetic replacement failure')
            return replace(source, target)
        with patch('offline_accounts.os.replace', side_effect=fail_current):
            with self.assertRaises(OSError):
                self.store.import_save('pirate01', self.document)
        self.assertEqual(self.store._path('pirate01').read_bytes(), self.original)
        new = set((self.store.runtime / 'backups').glob('*')) - self.backups
        self.assertEqual(len(new), 1)
        self.assertEqual(new.pop().read_bytes(), self.original)


if __name__ == '__main__':
    unittest.main()
