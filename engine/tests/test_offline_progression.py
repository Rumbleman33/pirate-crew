from copy import deepcopy
import csv
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
from offline_progression import OfflineProgression


class OfflineProgressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = PROJECT.parent / '.local' / 'test-work' / "offline-progression-tests"
        cls.work.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="progression-", dir=cls.work)
        cls.root = Path(cls.temp.name).resolve()
        (cls.root / "runtime").mkdir()
        OfflineAccounts(cls.root)
        (cls.root / "data").mkdir()
        for filename in ("catalog.json", "schemas.json"):
            shutil.copy2(PROJECT / "data" / filename, cls.root / "data" / filename)
        cls.store = OfflineStore(cls.root, PROJECT / "data" / "tables")
        cls.progression = OfflineProgression(cls.store)

    @classmethod
    def tearDownClass(cls):
        assert cls.root.is_relative_to(cls.work.resolve())
        cls.temp.cleanup()

    def setUp(self):
        self.state = self.store._seed("pirate01")
        self.progression.initialize_state(self.state)
        self.state.pop("_pendingBroadcasts", None)

    def call(self, cid, payload=None):
        return self.progression.dispatch(self.state, cid, payload or {})

    def give(self, ref_id, count):
        self.state["inventory"][str(ref_id)] = count

    def assertCode(self, code, function):
        with self.assertRaises(SimulationError) as raised:
            function()
        self.assertEqual(raised.exception.code, code)

    def sources(self, gid):
        return self.progression.stat_sources(self.state, {"generalId": gid})

    def totals(self, gid):
        combined = {}
        for source in self.sources(gid):
            for attr, value in source["attrs"].items():
                combined[attr] = combined.get(attr, 0) + value
        return combined

    def test_free_crew_slots_are_unrelated_to_selected_count(self):
        self.assertEqual(self.progression.active_fights(self.state), [1, 2, 3])
        self.assertEqual(self.progression.crew_capacity(self.state), 3)
        self.call(1305, {"generalId": 2000001})
        self.assertEqual(self.progression.active_fights(self.state), [1, 2, 3])
        self.assertEqual(self.call(1300)[0]["activeFights"], [1, 2, 3])

    def test_slot_unlock_requires_achievement_points_and_persists(self):
        self.assertCode("ACHIEVEMENT_POINTS_REQUIRED", lambda: self.call(1307, {"refId": 4}))
        self.give(109, 10)
        reply, changed, _ = self.call(1307, {"refId": 4})
        self.assertTrue(changed)
        self.assertEqual(reply["activeFights"], [1, 2, 3, 4])
        self.assertEqual(self.state["inventory"]["109"], 10)
        self.assertEqual(self.call(1307, {"refId": 4})[1], False)
        self.store._write("pirate01", self.state)
        self.assertEqual(self.store._read("pirate01")["activeFights"], [1, 2, 3, 4])

    def test_slot_unlock_is_sequential_and_not_a_character_recruit(self):
        self.give(109, 1000)
        self.assertCode("PREVIOUS_SLOT_REQUIRED", lambda: self.call(1307, {"refId": 5}))
        self.assertCode("UNKNOWN_CREW_SLOT", lambda: self.call(1307, {"generalId": 2000010}))
        self.assertEqual(set(self.state["generals"]), {"2000001", "2000010", "2000005"})

    def test_capacity_replacement_and_down_keep_ownership(self):
        self.call(1304, {"generalId": 2000005})
        self.state["generals"]["2000002"] = self.store._general_vo(2000002, 1, 0)
        self.assertCode("CREW_FULL", lambda: self.call(1304, {"generalId": 2000002}))
        self.call(1304, {"generalId": 2000002, "replaceGeneralId": 2000001})
        self.assertFalse(self.state["generals"]["2000001"]["isSelect"])
        self.assertTrue(self.state["generals"]["2000002"]["isSelect"])
        reply, _, _ = self.call(1305, {"generalId": 2000002})
        self.assertIn("general", reply)
        self.assertFalse(reply["general"]["isSelect"])
        self.assertIn("2000002", self.state["generals"])

    def test_migration_preserves_legacy_selection_and_earned_thresholds(self):
        self.state.pop("activeFights")
        self.give(109, 50)
        self.progression.initialize_state(self.state)
        self.assertEqual(self.state["activeFights"], [1, 2, 3, 4, 5])
        self.assertEqual(self.state["inventory"]["109"], 50)
        self.assertFalse(self.progression.initialize_state(self.state))

    def test_talent_uses_next_ref_and_exact_capture_costs(self):
        self.give(105, 10)
        reply, _, _ = self.call(1501)
        self.assertEqual(reply["info"]["refIds"], [1])
        self.assertEqual(self.state["inventory"]["105"], 8)
        self.assertEqual(self.totals(2000001), {2: 20.0})
        self.call(1501)
        self.assertEqual(self.totals(2000001), {1: 2.0, 2: 20.0})
        self.call(1501)
        before = deepcopy(self.state)
        self.assertCode("PLAYER_LEVEL_REQUIRED", lambda: self.call(1501))
        self.assertEqual(self.state, before)

    def test_advanced_talent_requires_basic_track_and_spends_red_diamond(self):
        self.give(1012, 4)
        self.assertCode("BASIC_TALENT_REQUIRED", lambda: self.call(1502))
        self.give(105, 10)
        self.call(1501)
        reply, _, _ = self.call(1502)
        self.assertEqual(reply["info"]["advanceIds"], [1])
        self.assertEqual(self.state["inventory"]["1012"], 3)
        self.assertEqual(self.totals(2000001), {2: 20.0, 8: 500.0})

    def test_treasure_activation_next_star_cost_and_associated_scope(self):
        self.give(6100001, 4)
        reply, _, _ = self.call(3321, {"refId": 6100001})
        self.assertEqual(reply["info"]["star"], 1)
        self.assertEqual(self.state["inventory"]["6100001"], 3)
        self.assertEqual(self.totals(2000001), {})
        self.assertEqual(self.totals(2000003), {1: 120.0, 2: 1200.0, 7: 30.0, 8: 30.0})
        self.call(3321, {"refId": 6100001})
        self.assertEqual(self.totals(2000003), {1: 240.0, 2: 2400.0, 7: 60.0, 8: 60.0})

    def test_treasure_material_is_spent_counted_and_limited_by_current_star(self):
        self.give(6100001, 1)
        self.give(1036, 50)
        self.call(3321, {"refId": 6100001})
        reply, _, _ = self.call(3322, {"refId": 6100001, "addNum": {"refId": 1036, "count": 5}})
        self.assertEqual(reply["info"]["materials"], [{"refId": 1036, "count": 5}])
        self.assertEqual(self.state["inventory"]["1036"], 45)
        self.assertEqual(self.totals(2000003)[1], 130)
        before = deepcopy(self.state)
        self.assertCode("MATERIAL_LIMIT", lambda: self.call(3322, {"refId": 6100001, "addNum": {"refId": 1036, "count": 16}}))
        self.assertEqual(self.state, before)

    def test_gem_master_uses_powder_and_current_cumulative_stage_only(self):
        self.give(1065, 25)
        self.call(10103)
        self.assertEqual(self.state["inventory"]["1065"], 15)
        self.assertEqual(self.totals(2000001), {1: 2.0})
        self.call(10103)
        self.assertEqual(self.state["inventory"]["1065"], 5)
        self.assertEqual(self.call(10100)[0]["bookStage"], 2)
        self.assertEqual(self.totals(2000001), {1: 2.0, 2: 20.0})
        before = deepcopy(self.state)
        self.assertCode("INSUFFICIENT_ITEMS", lambda: self.call(10103))
        self.assertEqual(self.state, before)

    def test_gem_equip_replace_undress_and_repeat_are_conservative(self):
        self.give(1000101, 2)
        self.give(1000102, 1)
        slot = {"generalId": 2000001, "slotRefId": 101, "itemId": 1000101}
        self.call(10101, {"slotInfos": [slot]})
        self.assertEqual(self.state["inventory"]["1000101"], 1)
        self.assertEqual(self.totals(2000001), {1: 50.0})
        self.assertEqual(self.call(10101, {"slotInfos": [slot]})[1], False)
        self.assertEqual(self.state["inventory"]["1000101"], 1)
        better = {**slot, "itemId": 1000102}
        self.call(10101, {"slotInfos": [better]})
        self.assertEqual(self.state["inventory"]["1000101"], 2)
        self.assertEqual(self.state["inventory"]["1000102"], 0)
        self.assertEqual(self.totals(2000001), {1: 100.0})
        self.call(10102, {"slotInfos": [better]})
        self.assertEqual(self.state["inventory"]["1000102"], 1)
        self.assertEqual(self.call(10102, {"slotInfos": [better]})[1], False)
        self.assertEqual(self.state["inventory"]["1000102"], 1)

    def test_gem_slot_type_star_and_batch_inventory_constraints(self):
        self.give(1000101, 1)
        self.give(1000201, 1)
        self.assertCode("GEM_TYPE_MISMATCH", lambda: self.call(10101, {"slotInfos": [{"generalId": 2000001, "slotRefId": 101, "itemId": 1000201}]}))
        self.assertCode("STAR_REQUIRED", lambda: self.call(10101, {"slotInfos": [{"generalId": 2000001, "slotRefId": 102, "itemId": 1000201}]}))
        slots = [{"generalId": gid, "slotRefId": 101, "itemId": 1000101} for gid in (2000001, 2000010)]
        before = deepcopy(self.state)
        self.assertCode("INSUFFICIENT_ITEMS", lambda: self.call(10101, {"slotInfos": slots}))
        self.assertEqual(self.state, before)

    def test_achievement_claim_grants_points_once_and_exposes_next_chain(self):
        self.state["player"]["level"] = 5
        self.call(1400)
        self.call(1402, {"type": 5, "refId": 30101})
        self.assertEqual(self.state["inventory"]["109"], 10)
        next_task = next(task for task in self.state["tasks"] if task["type"] == 5 and task["refId"] == 30102)
        self.assertEqual(next_task["state"], 1)
        self.assertCode("ALREADY_CLAIMED", lambda: self.call(1402, {"type": 5, "refId": 30101}))
        self.assertEqual(self.state["inventory"]["109"], 10)
        self.call(1307, {"refId": 4})
        self.assertIn(4, self.state["activeFights"])

    def test_cp_sources_include_achievement_percent_once_and_no_fake_free_roam_rewards(self):
        self.state["activeFights"] = list(range(1, 12))
        self.assertEqual(self.totals(2000001), {8: 500.0})
        self.state["settings"]["freeRoam"] = True
        before_points = self.state["inventory"].get("109", 0)
        self.call(1400)
        self.assertEqual(self.state["inventory"].get("109", 0), before_points)
        self.assertEqual(self.state.get("achievementClaims", []), [])

    def test_protocol_reply_shapes_and_legacy_reward_fallthrough(self):
        self.assertIsNone(self.call(1402, {"type": 2, "refId": 100010}))
        self.assertIsNone(self.call(999999))
        for cid in (1300, 1500, 3320, 10100):
            reply = self.call(cid)[0]
            filled = self.store._reply(cid, reply)
            schema_name = self.store.commands[cid]["response"]
            for field in self.store.schemas[schema_name]["fields"]:
                if field.get("required"):
                    self.assertIn(field["name"], filled)

    def test_integrated_cp_changes_follow_captured_power_weights(self):
        if not hasattr(self.store, "progression"):
            self.skipTest("Parent stat integration not installed")
        gid = "2000001"
        baseline = self.store.stats.evaluate(self.state)[gid]
        self.give(105, 10)
        self.call(1501)
        talent = self.store.stats.evaluate(self.state)[gid]
        self.assertEqual(talent["values"][2] - baseline["values"][2], 20)
        self.assertEqual(talent["power"] - baseline["power"], 20)
        self.give(1065, 30)
        self.call(10103)
        self.call(10103)
        master = self.store.stats.evaluate(self.state)[gid]
        self.assertEqual(master["values"][1] - talent["values"][1], 2)
        self.assertEqual(master["values"][2] - talent["values"][2], 20)
        self.assertEqual(master["power"] - talent["power"], 40)
        other_before = self.store.stats.evaluate(self.state)["2000010"]["power"]
        self.give(1000101, 1)
        self.call(10101, {"slotInfos": [{"generalId": 2000001, "slotRefId": 101, "itemId": 1000101}]})
        equipped = self.store.stats.evaluate(self.state)
        self.assertEqual(equipped[gid]["power"] - master["power"], 500)
        self.assertEqual(equipped["2000010"]["power"], other_before)

    def test_integrated_treasure_cp_is_scoped_and_crew_percent_is_applied(self):
        if not hasattr(self.store, "progression"):
            self.skipTest("Parent stat integration not installed")
        self.state["generals"]["2000003"] = self.store._general_vo(2000003, 1, 0)
        before = self.store.stats.evaluate(self.state)
        self.give(6100001, 1)
        self.call(3321, {"refId": 6100001})
        after = self.store.stats.evaluate(self.state)
        self.assertGreater(after["2000003"]["power"], before["2000003"]["power"])
        self.assertEqual(after["2000001"]["power"], before["2000001"]["power"])
        self.assertTrue(any(source["source"].startswith("Treasure 6100001") for source in after["2000003"]["sources"]))
        self.state["activeFights"] = list(range(1, 12))
        crew = self.store.stats.evaluate(self.state)
        self.assertEqual(crew["2000001"]["values"][2], int(after["2000001"]["values"][2] * 1.05))


if __name__ == "__main__":
    unittest.main()
