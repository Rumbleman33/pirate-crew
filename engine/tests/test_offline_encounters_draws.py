"""Behavioral checks for local encounter state and non-mutating draw experiments."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from offline_core import OfflineStore
from offline_accounts import OfflineAccounts
from offline_core import SimulationError
from offline_draws import OfflineDraws


class OfflineEncounterDrawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = PROJECT.parent / '.local' / 'test-work' / 'encounter-draw-tests'
        cls.work.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir=cls.work)
        cls.root = Path(cls.temp.name)
        (cls.root / 'runtime').mkdir()
        OfflineAccounts(cls.root)
        (cls.root / 'data/research').mkdir(parents=True)
        for file in ('catalog.json', 'schemas.json'):
            shutil.copy2(PROJECT / 'data' / file, cls.root / 'data' / file)
        shutil.copy2(PROJECT / 'data/research/halloween-research.json', cls.root / 'data/research/halloween-research.json')
        cls.store = OfflineStore(cls.root, PROJECT / 'data/tables')
        cls.draws = OfflineDraws(cls.store)

    @classmethod
    def tearDownClass(cls):
        assert cls.root.resolve().is_relative_to(cls.work.resolve())
        cls.temp.cleanup()

    def setUp(self):
        self.state = self.store._seed('pirate01')
        self.encounters = self.store.encounters
        self.clock = 1_800_000_000_000
        self.encounters.clock = lambda: self.clock
        self.sub_id = next(iter(self.encounters.subs))

    def call(self, cid, payload=None):
        return self.encounters.dispatch(self.state, cid, payload or {})[0]

    def enter(self):
        self.state['inventory'].update({str(i): 100000 for i in self.store.items if i not in self.store.equips})
        return self.call(52002, {'subActivityId': self.sub_id})['data']

    def hit(self, data, amount):
        attacker = next(s for s in data['sprites'] if s['type'] == 1)
        target = next(s for s in data['sprites'] if s['type'] == 2)
        self.call(50010, {'vo': [{'atkSpriteId': attacker['uid'], 'tarSpriteId': target['uid'], 'damage': amount}]})

    def test_bounty_damage_rank_and_wire_shapes(self):
        data = self.enter()
        self.hit(data, 7)
        rank = self.call(52005, {'subActivityId': self.sub_id})
        self.assertEqual(rank['myRank']['myScore'], 7)
        self.assertEqual(rank['rankInfos'][0]['playerScore'], 7)
        pushes = self.state['_pendingBroadcasts']
        self.assertTrue(any(p['id'] == 50007 for p in pushes))
        self.assertFalse(any(p['id'] == 50011 for p in pushes))

    def test_bounty_completion_grants_once_and_refreshes(self):
        data = self.enter()
        for _ in range(100):
            active = self.state['activeInstance']
            if active.get('settled'):
                break
            current = active['data']
            living = [s for s in current['sprites'] if s['type'] == 2 and s['labile']['hp']['cur'] > 0]
            self.assertTrue(living)
            actor = next(s for s in current['sprites'] if s['type'] == 1)
            self.call(50010, {'vo': [{'atkSpriteId': actor['uid'], 'tarSpriteId': s['uid'], 'damage': 10**15} for s in living]})
        self.assertTrue(self.state['activeInstance']['success'])
        self.assertTrue(self.state['activeInstance']['data']['rewards'])
        inventory = deepcopy(self.state['inventory'])
        self.hit(data, 10**15)
        self.assertEqual(self.state['inventory'], inventory)
        boss = self.state['bounties'][self.sub_id]
        self.assertEqual(boss['hpRate'], 0)
        expected_ms = max(1, int(self.encounters.subs[self.sub_id]['time'])) * 60000
        self.assertEqual(boss['nextRefreshTime'], self.clock + expected_ms)
        self.assertEqual(len(self.call(52007, {'subActivityId': self.sub_id})['records']), 1)
        settlement = next(p['data'] for p in self.state['_pendingBroadcasts'] if p['id'] == 52004)
        self.assertEqual(settlement['damage'], self.state['activeInstance']['damage'])
        self.assertEqual(settlement['rank'], 1)
        # desc switches the original UI into a PvP killer-name presentation.
        self.assertNotIn('desc', settlement)
        self.call(52003, {'subActivityId': self.sub_id})
        with self.assertRaises(SimulationError):
            self.call(52002, {'subActivityId': self.sub_id})
        self.clock += expected_ms + 1
        info = next(x for x in self.call(52001)['infos'] if x['subActivityId'] == self.sub_id)
        self.assertEqual(info['hpRate'], 10000)

    def test_invalid_bounty_is_atomic(self):
        before = deepcopy(self.state)
        with self.assertRaises(SimulationError):
            self.call(52002, {'subActivityId': 'not-a-bounty'})
        self.assertEqual(self.state, before)

    def test_leave_preserves_score_and_partial_hp(self):
        data = self.enter()
        self.hit(data, 100)
        result = self.call(52003, {'subActivityId': self.sub_id})
        self.assertEqual(result['curDamage'], 100)
        self.assertEqual(result['totalDamage'], 100)
        self.assertNotIn('activeInstance', self.state)
        self.assertLess(self.state['bounties'][self.sub_id]['hpRate'], 10000)

    def test_damage_ignores_unknown_targets_and_nonfinite_values(self):
        data = self.enter()
        before = deepcopy(self.state['activeInstance'])
        self.call(50010, {'vo': [{'atkSpriteId': -1, 'tarSpriteId': -2, 'damage': 100000}]})
        self.assertEqual(before, self.state['activeInstance'])
        self.hit(data, float('nan'))
        self.assertEqual(self.state['activeInstance']['damage'], 0)

    def test_free_roam_unlocks_every_world_region_without_quest_rewards(self):
        before = deepcopy(self.state)
        effective = set(self.store._effective_npc_ids(self.state))
        world = {int(r['npcId']) for r in self.store.table('SceneRegionRef') if 0 < int(r['sceneId']) < 100 and int(r['npcId'])}
        self.assertGreater(len(world), 100)
        self.assertTrue(world <= effective)
        self.assertEqual(self.state, before)
        self.state['settings']['freeRoam'] = False
        self.assertEqual(self.store._effective_npc_ids(self.state), sorted(self.state['unlockedNpcIds']))

    def test_legacy_avatar_migration_preserves_valid_cosmetics(self):
        self.state['player']['personality']['avatarRefId'] = 2000001
        self.store._write('pirate01', self.state)
        migrated = self.store._read('pirate01')
        self.assertEqual(migrated['player']['personality']['avatarRefId'], 20101)
        migrated['player']['personality']['avatarRefId'] = 20104
        self.store._write('pirate01', migrated)
        self.assertEqual(self.store._read('pirate01')['player']['personality']['avatarRefId'], 20104)

    def test_gm_travel_exits_an_encounter_without_granting_completion(self):
        self.enter()
        inventory = deepcopy(self.state['inventory'])
        self.store._write('pirate01', self.state)
        result = self.store.gm('pirate01', 'mapTransfer', '45')
        self.assertTrue(result['ok'])
        saved = self.store._read('pirate01')
        self.assertEqual(saved['scene']['mapId'], 45)
        self.assertNotIn('activeInstance', saved)
        self.assertEqual(saved['bounties'][self.sub_id]['innerCount'], 0)
        self.assertEqual(saved['inventory'], inventory)

    def test_draw_seed_reproduces_results_and_totals(self):
        payload = {'poolId': 'crew-1', 'pulls': 1000, 'seed': 'repeatable'}
        first = self.draws.simulate(payload)
        self.assertTrue(first['ok'], first)
        self.assertEqual(first, self.draws.simulate(payload))
        self.assertEqual(sum(r['hits'] for r in first['results']), 1000)
        self.assertEqual(sum(Fraction(r['probabilityExact']) for r in first['distribution']['entries']), 1)
        self.assertTrue(first['drawsTruncated'])
        self.assertEqual(len(first['draws']), 200)

    def test_draws_do_not_change_account_or_inventory(self):
        self.store._write('pirate01', self.state)
        before = (self.root / 'runtime/saves/pirate01.json').read_bytes()
        result = self.draws.simulate({'poolId': 'crew-2', 'pulls': 100, 'seed': 'no-mutation'})
        self.assertTrue(result['ok'])
        self.assertFalse(result['inventoryChanged'])
        self.assertEqual((self.root / 'runtime/saves/pirate01.json').read_bytes(), before)

    def test_custom_weights_and_fixed_guarantee(self):
        entries = [{'id': 'a', 'weight': 1}, {'id': 'b', 'weight': 3}]
        result = self.draws.simulate({'poolId': 'halloween-custom', 'pulls': 20, 'seed': 'guarantee', 'entries': entries,
                                      'pity': {'every': 5, 'targetIds': ['a'], 'resetOnNatural': False}})
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['totals']['pityHits'], 4)
        self.assertTrue(all(result['draws'][i]['id'] == 'a' for i in (4, 9, 14, 19)))
        self.assertAlmostEqual(sum(r['expectedHits'] for r in result['results']), 20)

    def test_unknown_seasonal_weights_are_never_invented(self):
        result = self.draws.simulate({'poolId': 'halloween-custom', 'pulls': 10})
        self.assertFalse(result['ok'])
        for bad in (-1, 'NaN', 'Infinity', None):
            with self.subTest(weight=bad):
                result = self.draws.simulate({'poolId': 'halloween-custom', 'pulls': 10, 'entries': [{'id': 'a', 'weight': bad}]})
                self.assertFalse(result['ok'])
        result = self.draws.simulate({'poolId': 'crew-1', 'pulls': 10, 'pity': {'every': 5, 'targetIds': ['a']}})
        self.assertFalse(result['ok'])


if __name__ == '__main__':
    unittest.main()
