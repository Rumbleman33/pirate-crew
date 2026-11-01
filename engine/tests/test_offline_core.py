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
from offline_core import GM_COMMANDS


class OfflineCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = PROJECT.parent / '.local' / 'test-work' / "offline-core-tests"
        cls.work.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="core-", dir=cls.work)
        cls.root = Path(cls.temp.name).resolve()
        (cls.root / "runtime").mkdir()
        OfflineAccounts(cls.root)

        cls.store = OfflineStore(cls.root, PROJECT / "data" / "tables")
        cls.store.catalog = json.loads((PROJECT / "data" / "catalog.json").read_text())
        cls.store.schemas = json.loads((PROJECT / "data" / "schemas.json").read_text())
        cls.store.commands = {row["id"]: row for row in cls.store.catalog["commands"]}
        cls.store.init_ids = set(cls.store.catalog["initCommandIds"])

    @classmethod
    def tearDownClass(cls):
        assert cls.root.is_relative_to(cls.work.resolve())
        cls.temp.cleanup()

    def setUp(self):
        self.store.reset("pirate01")
        self.store.reset("pirate02")

    def test_ten_distinct_accounts_and_hashed_credentials(self):
        accounts = self.store.accounts.list_accounts()
        self.assertEqual(len(accounts), 10)
        self.assertEqual(len({row["playerId"] for row in accounts}), 10)
        handout = (self.root / "TEST-LOGINS.txt").read_text()
        credentials = [line.split() for line in handout.splitlines() if line.startswith("pirate")]
        self.assertEqual(len(credentials), 10)
        self.assertEqual(len({row[1] for row in credentials}), 10)
        stored = (self.root / "runtime" / "accounts.json").read_text()
        for username, password in credentials:
            self.assertNotIn(password, stored)
            self.assertIsNotNone(self.store.login(username, password))
        self.assertIsNone(self.store.login("pirate01", "wrong-password"))

    def test_crafting_consumes_exact_shards_and_returns_only_new_copy(self):
        self.store.gm("pirate01", "addItem", "1_10000001_160")
        first = self.store.command("pirate01", 1103, {"refId": 4000001, "count": 1})
        second = self.store.command("pirate01", 1103, {"refId": 4000001, "count": 1})
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(second["reply"]["rewards"][0]["count"], 1)
        after = self.store.snapshot("pirate01")
        self.assertEqual(after["inventory"]["4000001"], 2)
        self.assertEqual(after["inventory"]["10000001"], 0)
        failed = self.store.command("pirate01", 1103, {"refId": 4000001, "count": 1})
        self.assertFalse(failed["ok"])
        self.assertEqual(self.store.snapshot("pirate01")["inventory"], after["inventory"])

    def test_gem_decomposition_aggregates_batch_and_cannot_duplicate_powder(self):
        self.store.gm("pirate01", "addItem", "1_1000101_3")
        result = self.store.command("pirate01", 1104, {"split": [{"refId": 1000101, "count": 1}, {"refId": 1000101, "count": 2}]})
        self.assertTrue(result["ok"])
        self.assertEqual(result["reply"]["rewards"][0]["count"], 450)
        before = self.store.snapshot("pirate01")["inventory"]
        self.assertEqual(before["1000101"], 0)
        self.assertEqual(before["1065"], 450)
        self.assertFalse(self.store.command("pirate01", 1104, {"split": [{"refId": 1000101, "count": 1}]})["ok"])
        self.assertEqual(self.store.snapshot("pirate01")["inventory"], before)

    def test_invalid_crafting_counts_and_non_gem_split_are_atomic(self):
        before = self.store.snapshot("pirate01")["inventory"]
        for payload in ({"refId": 4000001, "count": 0}, {"refId": 4000001, "count": -1}, {"refId": 999999, "count": 1}):
            self.assertFalse(self.store.command("pirate01", 1103, payload)["ok"])
        self.assertFalse(self.store.command("pirate01", 1104, {"split": [{"refId": 102, "count": 1}]})["ok"])
        self.assertEqual(self.store.snapshot("pirate01")["inventory"], before)

    def test_power_mutations_broadcast_current_power_with_increasing_revision(self):
        self.store.gm("pirate01", "addItem", "1_1065_100#1_105_100")
        talent = self.store.command("pirate01", 1501, {})
        master = self.store.command("pirate01", 10103, {})
        self.assertGreater(master["revision"], talent["revision"])
        after = self.store.snapshot("pirate01")
        broadcast = next(b for b in master["broadcasts"] if b["id"] == 1007)
        self.assertEqual(broadcast["data"]["attrs"], after["player"]["attrs"])

    def test_login_and_logout_session(self):
        line = next(line for line in (self.root / "TEST-LOGINS.txt").read_text().splitlines() if line.startswith("pirate01"))
        username, password = line.split()
        auth = self.store.login(username, password)
        self.assertEqual(self.store.account_for_token(auth["token"]), username)
        self.store.logout(auth["token"])
        self.assertIsNone(self.store.account_for_token(auth["token"]))

    def test_accounts_are_isolated_and_persist(self):
        before1 = self.store.snapshot("pirate01")["inventory"]["102"]
        before2 = self.store.snapshot("pirate02")["inventory"]["102"]
        result = self.store.gm("pirate01", "addItem", "1_102_7#1_103_3")
        self.assertTrue(result["ok"])
        self.assertEqual(self.store.snapshot("pirate01")["inventory"]["102"], before1 + 7)
        self.assertEqual(self.store.snapshot("pirate02")["inventory"]["102"], before2)
        reopened = OfflineStore(self.root, PROJECT / "data" / "tables")
        self.assertEqual(reopened.snapshot("pirate01")["inventory"]["102"], before1 + 7)

    def test_failed_gm_batch_is_atomic(self):
        before = self.store.snapshot("pirate01")
        result = self.store.gm("pirate01", "addItem", "1_102_7#1_999999999_10")
        self.assertFalse(result["ok"])
        self.assertEqual(self.store.snapshot("pirate01"), before)

    def test_all_gm_templates_have_handlers(self):
        for command, _, example, _ in GM_COMMANDS:
            with self.subTest(command=command):
                result = self.store.gm("pirate01", command, example)
                self.assertNotEqual(result.get("error", {}).get("code"), "UNSUPPORTED_GM_COMMAND")
                self.assertTrue(result["ok"], result.get("error"))
        state = self.store.snapshot("pirate01")
        self.assertEqual(len(state["generals"]), len(self.store.generals))
        self.assertEqual(len(state["potential"]), len(self.store.potentials))
        self.assertEqual(set(state["player"]["funcOpenRefIds"]), set(self.store.functions))
        self.assertTrue(state["messages"])
        self.assertTrue(state["auctions"])

    def test_gm_level_is_free_and_broadcasts_level(self):
        before = self.store.snapshot("pirate01")["inventory"]
        result = self.store.gm("pirate01", "level", "20")
        self.assertTrue(result["ok"])
        self.assertEqual(self.store.snapshot("pirate01")["player"]["level"], 20)
        self.assertEqual(self.store.snapshot("pirate01")["inventory"], before)
        info = next(row for row in result["broadcasts"] if row["id"] == 1015)
        self.assertEqual(info["data"]["attrs"][0]["int64Value"], 20)

    def test_normal_upgrade_spends_original_cost(self):
        before = self.store.snapshot("pirate01")
        result = self.store.command("pirate01", 1301, {"generalId": 2000010})
        self.assertTrue(result["ok"])
        self.assertEqual(result["reply"]["general"]["level"], 2)
        after = self.store.snapshot("pirate01")
        self.assertEqual(after["inventory"]["103"], before["inventory"]["103"] - 5)
        self.assertEqual(after["inventory"]["2000010"], before["inventory"]["2000010"] - 5)
        self.store.gm("pirate01", "subItem", "1_103_1000000000")
        before = self.store.snapshot("pirate01")
        rejected = self.store.command("pirate01", 1301, {"generalId": 2000010})
        self.assertFalse(rejected["ok"])
        self.assertEqual(rejected["error"]["code"], "INSUFFICIENT_ITEMS")
        self.assertEqual(self.store.snapshot("pirate01"), before)

    def test_mail_claim_cannot_duplicate_reward(self):
        before = self.store.snapshot("pirate01")["inventory"]["102"]
        self.assertTrue(self.store.command("pirate01", 1703, {"emailId": 1})["ok"])
        after = self.store.snapshot("pirate01")["inventory"]["102"]
        self.assertEqual(after - before, 1000)
        self.store.command("pirate01", 1703, {"emailId": 1})
        self.assertEqual(self.store.snapshot("pirate01")["inventory"]["102"], after)

    def test_shop_cost_and_reward(self):
        before = self.store.snapshot("pirate01")["inventory"]
        result = self.store.command("pirate01", 1802, {"shopId": 1, "shopItemRefId": 1001, "count": 1})
        self.assertTrue(result["ok"])
        after = self.store.snapshot("pirate01")["inventory"]
        self.assertEqual(after["101"], before["101"] - 10)
        self.assertEqual(after["105"], before.get("105", 0) + 100)

    def test_import_keeps_target_account_identity(self):
        document = self.store.export_save("pirate01")
        document["state"]["inventory"]["102"] = 55
        state = self.store.import_save("pirate02", document)
        self.assertEqual(state["username"], "pirate02")
        self.assertEqual(state["playerId"], self.store.accounts.public_account("pirate02")["playerId"])
        self.assertEqual(state["inventory"]["102"], 55)
        self.assertNotEqual(self.store.snapshot("pirate01")["inventory"]["102"], 55)

    def test_unknown_commands_are_explicit_and_do_not_mutate(self):
        before = self.store.snapshot("pirate01")
        result = self.store.command("pirate01", 2411, {})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "UNSUPPORTED_OFFLINE")
        self.assertEqual(self.store.snapshot("pirate01"), before)

    def test_all_initialization_replies_have_required_fields(self):
        def check(name, value):
            for field in self.store.schemas.get(name, {}).get("fields", []):
                key = field["name"]
                if field.get("required"):
                    self.assertIn(key, value, (name, key))
                if key in value and field["type"] == "message":
                    children = value[key] if field.get("repeated") else [value[key]]
                    for child in children:
                        check(field["message"], child)
        for cid in sorted(self.store.init_ids | {1001}):
            with self.subTest(command=cid):
                result = self.store.command("pirate01", cid, {})
                self.assertTrue(result["ok"], result.get("error"))
                check(self.store.commands[cid].get("response"), result["reply"])


    def test_party_slots_use_original_slot_references(self):
        result = self.store.command("pirate01", 1300, {})
        valid = {int(row["refId"]) for row in self.store.table("GeneralFightRef")}
        self.assertTrue(result["reply"]["activeFights"])
        self.assertTrue(set(result["reply"]["activeFights"]).issubset(valid))

    def test_server_age_updates_open_timestamp_without_spending(self):
        from offline_core import now_ms
        start = self.store.snapshot("pirate01")
        result = self.store.gm("pirate01", "serverAge", "730")
        self.assertTrue(result["ok"])
        after = self.store.snapshot("pirate01")
        self.assertEqual(after["settings"]["serverAgeDays"], 730)
        self.assertLess(abs((now_ms() - after["player"]["openServerTime"]) - 730 * 86400000), 5000)
        self.assertEqual(start["inventory"], after["inventory"])

    def test_power_is_positive_and_updates_after_character_upgrade(self):
        def power():
            return next(a["attrValue"] for a in self.store.snapshot("pirate01")["player"]["attrs"] if a["attrType"] == 1000)
        before = power()
        self.assertGreater(before, 0)
        self.assertTrue(self.store.command("pirate01", 1301, {"generalId": 2000001})["ok"])
        self.assertGreater(power(), before)

    def test_usopp_npc_spends_three_meat_and_cannot_duplicate_reward(self):
        before = self.store.snapshot("pirate01")["inventory"]
        result = self.store.command("pirate01", 50102, {"npcId": 100001})
        self.assertTrue(result["ok"], result.get("error"))
        after = self.store.snapshot("pirate01")["inventory"]
        self.assertEqual(after["103"], before["103"] - 3)
        self.assertEqual(after["2000010"], before["2000010"] + 15)
        self.store.command("pirate01", 50102, {"npcId": 100001})
        self.assertEqual(self.store.snapshot("pirate01")["inventory"], after)
        self.assertIn(100001, self.store.command("pirate01", 50103, {})["reply"]["npcIds"])

    def test_wood_unlock_consumes_captured_cost_and_persists(self):
        before = self.store.snapshot("pirate01")["inventory"]["104"]
        result = self.store.command("pirate01", 50102, {"npcId": 4})
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(self.store.snapshot("pirate01")["inventory"]["104"], before - 10)
        self.assertIn(4, self.store.snapshot("pirate01")["unlockedNpcIds"])

    def test_no_pet_is_forced_to_appear_on_a_new_captain(self):
        info = self.store.command("pirate01", 2600, {})["reply"]
        self.assertEqual(info["appearId"], 0)
        self.assertEqual(info["pets"], [])

    def test_panda_skin_is_owned_equipped_and_broadcast_to_scene(self):
        result = self.store.gm("pirate01", "equipSkin", "16055005")
        self.assertTrue(result["ok"], result.get("error"))
        state = self.store.snapshot("pirate01")
        self.assertEqual(state["generals"]["2000055"]["skinId"], 16055005)
        self.assertTrue(state["generals"]["2000055"]["isSelect"])
        self.assertIn("16055005", state["generalSkins"])
        self.assertTrue(any(b["id"] == 1302 for b in result["broadcasts"]))

    def test_bounty_list_contains_alive_original_bosses(self):
        result = self.store.command("pirate01", 52001, {})
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["reply"]["infos"]), len(self.store.boss_subs))
        self.assertTrue(all(b["hpRate"] > 0 for b in result["reply"]["infos"]))

    def test_starting_quest_chain_tracks_kills_rescue_wood_and_fog(self):
        self.store.command("pirate01", 50006, {"monsters": [{"uid": n, "id": 100101} for n in range(71, 74)]})
        kills = self.store.command("pirate01", 50005, {"vos": [{"uid": n} for n in range(71, 74)]})
        self.assertTrue(any(b["id"] == 1401 for b in kills["broadcasts"]))
        first = next(task for task in self.store.command("pirate01", 1400, {})["reply"]["taskInfos"] if task["type"] == 2 and task["state"] != 3)
        self.assertEqual((first["refId"], first["state"], first["progress"]), (100010, 2, 3))
        self.assertTrue(self.store.command("pirate01", 1402, {"type": 2, "refId": 100010})["ok"])
        self.assertFalse(self.store.command("pirate01", 1402, {"type": 2, "refId": 100010})["ok"])
        self.store.command("pirate01", 50102, {"npcId": 100001})
        self.assertTrue(self.store.command("pirate01", 1402, {"type": 2, "refId": 100020})["ok"])
        before = self.store.snapshot("pirate01")["inventory"]["104"]
        self.store.command("pirate01", 50006, {"loots": [{"uid": 81, "id": 100101}]})
        self.store.command("pirate01", 50005, {"vos": [{"uid": 81}]})
        self.assertEqual(self.store.snapshot("pirate01")["inventory"]["104"], before + 2)
        self.assertTrue(self.store.command("pirate01", 1402, {"type": 2, "refId": 100021})["ok"])
        self.store.command("pirate01", 50102, {"npcId": 1001})
        self.assertTrue(self.store.command("pirate01", 1402, {"type": 2, "refId": 100030})["ok"])
        self.assertGreater(self.store.snapshot("pirate01")["player"]["level"], 1)

    def test_halloween_and_chubby_buggy_skins_can_be_equipped(self):
        for skin_id in [16056006, 16059004, 16061004, 16062006, 16070001, 16052005]:
            with self.subTest(skin_id=skin_id):
                result = self.store.gm("pirate01", "equipSkin", str(skin_id))
                self.assertTrue(result["ok"], result.get("error"))
                self.assertIn(str(skin_id), self.store.snapshot("pirate01")["generalSkins"])

    def test_bounty_entry_damage_and_reward_settlement_are_local_and_idempotent(self):
        self.store.gm("pirate01", "addItem", "1_123_2")
        entered = self.store.command("pirate01", 52002, {"subActivityId": "wroldBossSub_1", "generals": []})
        self.assertTrue(entered["ok"], entered.get("error"))
        data = entered["reply"]["data"]
        boss = next(sprite for sprite in data["sprites"] if sprite["type"] == 2)
        actor = next(sprite for sprite in data["sprites"] if sprite["type"] == 1)
        self.assertEqual(self.store.snapshot("pirate01")["inventory"]["123"], 1)
        payload = {"vo": [{"atkSpriteId": actor["uid"], "tarSpriteId": boss["uid"], "refId": 1, "damage": boss["labile"]["hp"]["max"]}]}
        result = self.store.command("pirate01", 50010, payload)
        self.assertTrue(result["ok"], result.get("error"))
        self.assertTrue(any(b["id"] == 50007 for b in result["broadcasts"]))
        self.assertTrue(any(b["id"] == 52004 for b in result["broadcasts"]))
        saved = self.store.snapshot("pirate01")["inventory"]
        self.store.command("pirate01", 50010, payload)
        self.assertEqual(self.store.snapshot("pirate01")["inventory"], saved)
        leave = self.store.command("pirate01", 52003, {"subActivityId": "wroldBossSub_1"})
        self.assertTrue(leave["ok"], leave.get("error"))
        self.assertEqual(leave["reply"]["info"]["hpRate"], 0)

    def test_daily_sign_in_cannot_be_claimed_twice(self):
        first = self.store.command("pirate01", 1201, {})
        self.assertTrue(first["ok"], first.get("error"))
        self.assertFalse(self.store.command("pirate01", 1201, {})["ok"])
        self.assertEqual(self.store.command("pirate01", 1200, {})["reply"]["info"]["days"], [1])

    def test_english_reference_display_preserves_protocol_ids(self):
        from offline_english import display_row, english
        result = display_row("GeneralSkinRef", {"skinId": "16056006", "name": "万圣节·大和", "cost": "1_16056006_1"})
        self.assertEqual(result, {"skinId": "16056006", "name": "Halloween Yamato", "cost": "1_16056006_1"})
        self.assertEqual(english("乌塔-专属-效果5"), "Uta: exclusive effect 5")
        self.assertEqual(english('["每日额外领取绑钻"]'), '["Extra Bound Diamonds every day"]')

    def test_level_115_power_uses_captured_star_and_owned_class_boosts(self):
        import math
        state = self.store.snapshot("pirate01")
        state["generals"]["2000055"] = self.store._general_vo(2000055, 115, 24, True)
        stats = self.store.stats.evaluate(state)["2000055"]
        # Star 24's cumulative 272.25%, plus seven 5% class boosts from this
        # captain's level milestones. No arbitrary per-star multiplier.
        self.assertEqual(stats["values"][1], math.floor(2330 * (1 + (27225 + 3500) / 10000)))
        self.assertEqual(stats["values"][2], math.floor(23260 * (1 + (27225 + 3500) / 10000)))
        self.assertEqual(stats["power"], stats["values"][1] * 10 + stats["values"][2])
        state["generals"]["2000004"] = self.store._general_vo(2000004, 115, 0, False)
        boosted = self.store.stats.evaluate(state)["2000055"]
        self.assertGreater(boosted["power"], stats["power"])

    def test_equipment_crit_and_potential_contribute_to_power(self):
        state = self.store.snapshot("pirate01")
        before = self.store.stats.evaluate(state)["2000001"]
        state["equipment"][0]["generalId"] = 2000001
        after = self.store.stats.evaluate(state)["2000001"]
        self.assertEqual(after["values"][3], 11)
        self.assertEqual(after["power"] - before["power"], 28 * 10 + 11 * 25)

    def test_star_bonus_rows_do_not_replace_active_skills_at_low_levels(self):
        for level in [1, 5, 15, 24, 115]:
            self.assertTrue(self.store._general_vo(2000055, level, 0)["skillIds"], level)

    def test_local_sessions_survive_restart_without_raw_token_on_disk(self):
        credentials = dict(__import__('re').findall(r"^(pirate\d{2})\s+(\S+)$", (self.root / "TEST-LOGINS.txt").read_text(encoding="utf-8"), __import__('re').M))
        auth = self.store.login("pirate01", credentials["pirate01"])
        restarted = OfflineStore(self.root, PROJECT / "data" / "tables")
        self.assertEqual(restarted.account_for_token(auth["token"]), "pirate01")
        self.assertNotIn(auth["token"], (self.root / "runtime" / "sessions.json").read_text())
        restarted.accounts.logout(auth["token"])
        self.assertIsNone(OfflineStore(self.root, PROJECT / "data" / "tables").account_for_token(auth["token"]))

    def test_local_world_rewards_each_registered_monster_once(self):
        self.assertTrue(self.store.command("pirate01", 50001, {"refId": 1})["ok"])
        start = self.store.snapshot("pirate01")["inventory"]["102"]
        self.store.command("pirate01", 50006, {"monsters": [{"uid": 42, "id": next(iter(self.store.monsters))}]})
        first = self.store.command("pirate01", 50005, {"vos": [{"uid": 42}]})
        second = self.store.command("pirate01", 50005, {"vos": [{"uid": 42}]})
        self.assertEqual(len(first["reply"]["ops"]), 1)
        self.assertEqual(second["reply"]["ops"], [])
        self.assertEqual(self.store.snapshot("pirate01")["inventory"]["102"], start + 10)

if __name__ == "__main__":
    unittest.main()
