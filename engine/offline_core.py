"""Persistent offline game simulation using the recovered original reference tables.

This is a test-server reimplementation, not recovered production server code. Commands
are labelled as simulated, client actions, empty initialization stubs, or unsupported.
All state belongs to an offline account. This module makes no network requests.
"""
from __future__ import annotations

from copy import deepcopy
import csv
import json
import math
from pathlib import Path
import re
import secrets
import threading
import time
from typing import Any

from offline_accounts import OfflineAccounts, atomic_json
from offline_english import english
from offline_stats import OfflineStats
from offline_progression import OfflineProgression
from offline_encounters import OfflineEncounters
from offline_companions import OfflineCompanions
from offline_workshop import OfflineWorkshop
from offline_equipment import OfflineEquipment
from offline_voyage import OfflineVoyage
from offline_systems import OfflineSystems
from offline_world import OfflineWorld
from offline_stages import OfflineStages


DEV_CAPTURE = Path("/unavailable")
OLD_METADATA = Path("/unavailable")
MAX_QUANTITY = 1_000_000_000_000
GM_COMMANDS = [
    ("addItem", "Grant items", "1_102_100", "inventory"),
    ("addEquip", "Create actual gear pieces from EquipRef", "11011_1", "inventory"),
    ("completeVoyageTasks", "Mark current One Piece objectives complete for offline testing; claim and upgrade normally", "", "progression"),
    ("stockTestItems", "Restock all test items and resources without upgrading anything", "", "inventory"),
    ("subItem", "Remove items", "1_102_1", "inventory"),
    ("level", "Set player level", "20", "progression"),
    ("serverAge", "Set simulated server age in days", "365", "world"),
    ("freeRoam", "Explore every world island and fog area without quest gates", "1", "world"),
    ("equipSkin", "Own, equip and deploy a captured character skin", "16055005", "characters"),
    ("generalMax", "Own and max all captured characters", "", "characters"),
    ("potentialAll", "Max captured potential nodes", "", "characters"),
    ("talentAll", "Unlock every captured normal and advanced talent for offline testing", "", "progression"),
    ("openAllFunc", "Unlock every captured feature", "", "features"),
    ("rebirthAll", "Revive local scene actors", "", "scene"),
    ("mapTransfer", "Change local map", "1", "scene"),
    ("moveSpeed", "Set local movement speed", "1", "scene"),
    ("setInsLv", "Set local instance level", "101_1", "instances"),
    ("addMail", "Create local test mail", "Offline test mail|Welcome|1_102_100", "mail"),
    ("sendSystemMsg", "Add a local system message", "Offline test message", "messages"),
    ("sendRollNotice", "Add a local announcement", "Offline announcement", "messages"),
    ("tower", "Set local tower floor", "20", "instances"),
    ("mainTask", "Set local main task", "100010", "tasks"),
    ("task", "Complete a local task", "100010", "tasks"),
    ("openTipShow", "Preview local feature-unlock tip", "100", "client"),
    ("addMonster", "Spawn a local test monster", "100101_1", "scene"),
    ("actorSpine", "Open character asset preview", "", "client"),
    ("monsterSpine", "Open monster asset preview", "", "client"),
    ("TrajectorySpine", "Open projectile asset preview", "", "client"),
    ("limitAttr", "Toggle a local temporary attribute", "1", "attributes"),
    ("guildAuction", "Record a simulated guild auction", "test", "guild"),
    ("prisonIn", "Enter local prison state", "", "scene"),
    ("prisonOut", "Leave local prison state", "", "scene"),
    ("stageFb", "Open local stage instance", "27999", "instances"),
    ("hide", "Hide/show local game interface", "1", "client"),
    ("LayaGC", "Release unused client rendering resources", "", "client"),
]


class SimulationError(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)


def integer(value: Any, default=0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return default


def now_ms() -> int:
    return int(time.time() * 1000)


def item_vo(ref_id: int, count: int) -> dict:
    return {"refId": ref_id, "count": count, "attrs": []}


class OfflineStore:
    def __init__(self, root: str | Path, data_path: str | Path | None = None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.accounts = OfflineAccounts(self.root)
        self.runtime = self.root / "runtime"
        self.saves = self.runtime / "saves"
        self.saves.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._tables: dict[str, list[dict]] = {}
        candidates = [Path(data_path)] if data_path else [self.root / "data" / "tables", self.root / "static" / "data", DEV_CAPTURE]
        self.data_path = next((path for path in candidates if (path / "GeneralRef.csv").exists()), candidates[0])
        self.catalog = self._metadata("catalog.json", {"commands": [], "initCommandIds": []})
        self.schemas = self._metadata("schemas.json", {})
        self.commands = {integer(row["id"]): row for row in self.catalog.get("commands", [])}
        self.init_ids = set(self.catalog.get("initCommandIds", []))
        self._load_indexes()
        self.progression = OfflineProgression(self)
        self.stats = OfflineStats(self)
        self.encounters = OfflineEncounters(self)
        self.companions = OfflineCompanions(self)
        self.workshop = OfflineWorkshop(self)
        self.equipment_rules = OfflineEquipment(self)
        self.voyage = OfflineVoyage(self)
        self.systems = OfflineSystems(self)
        self.world = OfflineWorld(self)
        self.stages = OfflineStages(self)
        for account in self.accounts.list_accounts():
            if not self._path(account["username"]).exists():
                self._write(account["username"], self._seed(account["username"]))

    def _metadata(self, name: str, fallback: Any) -> Any:
        for base in (self.root / "data", self.root / "static" / "data", OLD_METADATA):
            path = base / name
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        return fallback

    def table(self, name: str) -> list[dict]:
        name = Path(name).name.removesuffix(".csv")
        if name not in self._tables:
            path = self.data_path / (name + ".csv")
            if path.exists():
                with path.open(encoding="utf-8-sig", newline="") as handle:
                    self._tables[name] = list(csv.DictReader(handle))
            else:
                self._tables[name] = []
        return self._tables[name]

    def _load_indexes(self):
        def index(name, key="refId"):
            return {integer(row.get(key)): row for row in self.table(name)}
        self.generals = index("GeneralRef")
        self.items = index("ItemRef")
        self.equips = index("EquipRef")
        self.pets = index("PetRef")
        self.mounts = index("MountRef")
        self.functions = index("FnRef")
        self.scenes = index("SceneRef")
        self.npcs = index("NpcRef")
        self.general_skins = index("GeneralSkinRef", "skinId")
        self.global_config = next(iter(self.table("GlobalRef")), {})
        self.boss_subs = {row["subId"]: row for row in self.table("WorldBossSubRef")}
        self.instances = index("InsRef")
        self.instance_refs = {(integer(r["insId"]), integer(r["lv"])): r for r in self.table("InsLvRef")}
        self.instance_waves = {}
        for row in self.table("InsRefreshRef"):
            self.instance_waves.setdefault(integer(row["refId"]), []).append(row)
        self.monsters = index("MonsterRef")
        self.scene_loot = index("SceneLootRef")
        self.potentials = index("PotentialRef")
        self.task_refs = index("TaskMainRef")
        self.player_levels = index("PlayerLevelRef", "lv")
        self.shop_items = index("ShopItemRef", "id")
        self.general_levels = {(integer(r["generalId"]), integer(r["lv"])): r for r in self.table("GeneralLvRef")}
        self.general_stars = {(integer(r["generalId"]), integer(r["star"])): r for r in self.table("GeneralStarRef")}
        self.potential_levels = {(integer(r["refId"]), integer(r["lv"])): r for r in self.table("PotentialLvRef")}
        self.general_skills = {}
        for row in self.table("GeneralSkillRef"):
            self.general_skills.setdefault(integer(row.get("generalId")), []).append(row)

    def initialize_demo_accounts(self) -> list[dict]:
        return self.accounts.initialize_demo_accounts()

    def login(self, username: str, password: str) -> dict | None:
        return self.accounts.login(username, password)

    def account_for_token(self, token: str | None) -> str | None:
        return self.accounts.account_for_token(token)

    def logout(self, token: str | None):
        self.accounts.logout(token)

    def _username(self, account: str | dict) -> str:
        username = account.get("username") if isinstance(account, dict) else account
        self.accounts.public_account(username)
        return username

    def _path(self, username: str) -> Path:
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,23}", username):
            raise SimulationError("INVALID_ACCOUNT", "Unknown offline test account")
        return self.saves / (username + ".json")

    def _read(self, username: str) -> dict:
        state = json.loads(self._path(username).read_text(encoding="utf-8"))
        migrated=integer(state.get('saveSchemaVersion'))<14
        if migrated:
            backup=self.saves.parent/'backups'/(username+'-before-v14.json')
            if not backup.exists():atomic_json(backup,state)
            state['saveSchemaVersion']=14
            state['settings'].setdefault('autoVoyageObjectives',True)
        state.setdefault("generalSkins", {})
        state.setdefault("unlockedNpcIds", [])
        state.setdefault("unlockedBossIds", [])
        state.setdefault("progression", {"kills": {}, "gathered": {}, "mapsVisited": [state["scene"]["mapId"]]})
        for task in state["tasks"]:
            if task.get("type") == 1 and task["refId"] in self.task_refs:
                task["type"] = 2
        state["settings"].setdefault("freeRoam", True)
        # Early sandbox saves used a character ID where the client expects a
        # PersonalityRef avatar. Preserve every valid cosmetic selection.
        personality = state["player"].setdefault("personality", {})
        avatars = {integer(r["refId"]) for r in self.table("PersonalityRef") if integer(r["type"]) == 2}
        if integer(personality.get("avatarRefId")) not in avatars:
            personality["avatarRefId"] = 20101
        self.progression.initialize_state(state)
        self._sync_tasks(state)
        state["settings"].setdefault("petAppearId", 0)
        repaired = self.companions.repair(state) or migrated
        repaired = self.systems.repair(state) or repaired
        repaired = self.equipment_rules.repair(state) or repaired
        for general in state["generals"].values():
            if not general.get("skillIds"):
                general["skillIds"] = self._general_vo(general["generalId"], general["level"], general["star"])["skillIds"]
        for number, equip in enumerate(state["equipment"], 1):
            if not str(equip["equipId"]).isdigit():
                equip["equipId"] = 8800000000000 + number
            equip['equipId']=str(equip['equipId'])
        self._sync_player_attrs(state)
        self.progression.sync_achievements(state)
        if repaired:
            self._write(username, state)
        return state

    def prepare_test_sandbox(self, account: str | dict, force=False) -> dict:
        """One-time additive stock grant. Existing purchases and upgrades survive."""
        with self._lock:
            username = self._username(account)
            state = self._read(username)
            if force or integer(state['settings'].get('testStockVersion')) < 5:
                self._stock_test_items(state)
                self._write(username, state)
            return deepcopy(state)

    def _stock_test_items(self, state):
        # EXP and earned achievement/rein counters represent progress, not
        # spendable supplies. Keep those unchanged so players choose progression.
        progress_ids = {106, 107, 108, 109, 110, 113}
        targets = {rid: 9999 for rid,row in self.items.items() if rid not in progress_ids and integer(row.get('type'))!=3}
        # Captured high-cost resources get enough for substantial experimentation.
        for path in ([] if hasattr(self, '_test_stock_targets') else self.data_path.glob('*.csv')):
            for row in self.table(path.stem):
                for key, value in row.items():
                    if 'cost' not in key.lower() and key not in ('reqGoods', 'consume'):continue
                    if not isinstance(value, str):continue
                    for match in re.finditer(r'(?:^|#)1_(\d+)_(\d+)(?=#|$)', value):
                        rid, count = map(int, match.groups())
                        if rid in targets:targets[rid] = max(targets[rid], min(1_000_000_000, count * 100))
        targets.update({101: 100_000_000, 111: 100_000_000, 102: 10_000_000_000, 103: 100_000_000, 104: 100_000_000, 105: 100_000_000})
        targets.update({1006:1_000_000,1007:1_000_000,1008:1_000_000,1013:1_000_000_000,**{rid:1_000_000 for rid in range(1014,1021)}})
        targets = getattr(self, '_test_stock_targets', targets)
        self._test_stock_targets = targets
        for rid, count in targets.items():
            state['inventory'][str(rid)] = max(integer(state['inventory'].get(str(rid))), count)
        state['inventory']['109'] = max(integer(state['inventory'].get('109')),999_999_999)
        if integer(state['settings'].get('gearStockVersion'))<1:
            sequence=max([integer(e['equipId'])-8800000000000 for e in state['equipment']]+[0])+1
            counts={}
            for equip in state['equipment']:counts[integer(equip['equipRefId'])]=counts.get(integer(equip['equipRefId']),0)+1
            for rid in self.equips:
                for _ in range(max(0,3-counts.get(rid,0))):
                    state['equipment'].append(self._equip_vo(rid,sequence));sequence+=1
            state['settings']['gearStockVersion']=1
        state['settings']['testStockVersion'] = 5
        state['settings']['equipmentCapacity'] = 10000

    def _write(self, username: str, state: dict):
        self.voyage.info(state)
        self.progression.initialize_state(state)
        self._sync_player_attrs(state)
        self.progression.sync_achievements(state)
        state["updatedAt"] = max(now_ms(), integer(state.get("updatedAt")) + 1)
        atomic_json(self._path(username), state)

    def _seed(self, username: str) -> dict:
        account = self.accounts.public_account(username)
        stamp = now_ms()
        starters = [value for value in [2000001, 2000010, 2000005] if value in self.generals] or list(self.generals)[:3]
        inventory = {"101": 10000, "102": 1000000, "103": 10000, "104": 10000, "1001": 1000}
        inventory.update({str(gid): 500 for gid in starters})
        first_scene = next(iter(self.scenes.values()), {})
        birth = first_scene.get("birthPos", "1707_5222").split("_")
        first_task = next(iter(self.task_refs), 100010)
        tasks = [{"type": 2, "refId": first_task, "state": 1, "progress": 0, "extInfo": ""}]
        state = {
            "schemaVersion": 1, "mode": "offline", "username": username, "account": account,
            "playerId": account["playerId"], "createdAt": stamp, "updatedAt": stamp,
            "player": {"playerId": account["playerId"], "nickname": account["displayName"], "gender": 1,
                       "funcOpenRefIds": sorted(self.functions), "personality": {"avatarRefId": 20101, "avatarFrameRefId": 30001, "title": 0, "mainRoleSkin": 0, "chatFrameRefId": 40001},
                       "level": 1, "vipLevel": 0, "attrs": [], "desc": "Offline test captain", "createTime": stamp,
                       "openServerTime": stamp - 365 * 86400000, "lastOfflineTime": stamp, "loginDays": 1,
                       "rewardPreviewIds": [], "cumulativeChargeDailyVipExp": 0, "changeNameCount": 0},
            "inventory": inventory, "generals": {}, "equipment": [],
            "pets": [], "mounts": [], "generalSkins": {}, "unlockedNpcIds": [], "unlockedBossIds": [],
            "potential": {}, "tasks": tasks, "mail": [], "shopPurchases": {}, "appends": {}, "doneValues": {},
            "progression": {"kills": {}, "gathered": {}, "mapsVisited": [integer(first_scene.get("refId"), 1)]},
            "scene": {"mapId": integer(first_scene.get("refId"), 1), "x": integer(birth[0]), "y": integer(birth[-1]), "moveSpeed": 1, "monsters": [], "dead": False, "prison": False, "stage": 0},
            "instanceLevels": {}, "towerFloor": 1, "limitAttrs": {}, "auctions": [], "messages": [],
            "settings": {"fullGM": True, "allFunctionsOpen": True, "hideUI": False, "serverAgeDays": 365, "petAppearId": 0, "freeRoam": True}, "clientActions": [], "claimedRewards": [],
            "simulation": {"kind": "local-reimplementation", "source": "captured-client-tables", "serverLogicAvailable": False,
                           "notes": "Normal progression uses captured costs; combat and many server systems are local approximations."},
        }
        for gid in starters:
            state["generals"][str(gid)] = self._general_vo(gid, 1, 0, selected=(gid in starters[:2]))
        state["equipment"] = [self._equip_vo(ref_id, index + 1) for index, ref_id in enumerate(list(self.equips)[:8])]
        state["mail"].append(self._mail(1, "Offline welcome", "Your test account has full local GM access.", "1_102_1000#1_103_100"))
        self.progression.initialize_state(state)
        return state

    def snapshot(self, account: str | dict) -> dict:
        with self._lock:
            return deepcopy(self._read(self._username(account)))

    def reset(self, account: str | dict) -> dict:
        with self._lock:
            username = self._username(account)
            state = self._seed(username)
            self._write(username, state)
            return deepcopy(state)

    def export_save(self, account: str | dict) -> dict:
        return {"format": "pirates-offline-save", "version": 1, "state": self.snapshot(account)}

    def import_save(self, account: str | dict, document: dict) -> dict:
        with self._lock:
            username = self._username(account)
            supplied = document.get("state", document)
            if not isinstance(supplied, dict) or supplied.get("mode") != "offline":
                raise SimulationError("INVALID_SAVE", "Select an offline game save exported by this build")
            if not isinstance(supplied.get("inventory"), dict) or not isinstance(supplied.get("generals"), dict):
                raise SimulationError("INVALID_SAVE", "Offline save is missing inventory or roster")
            state = deepcopy(supplied)
            identity = self.accounts.public_account(username)
            state.update(username=username, account=identity, playerId=identity["playerId"], mode="offline")
            state.setdefault("player", {}).update(playerId=identity["playerId"], nickname=identity["displayName"])
            for key, count in state["inventory"].items():
                if integer(count, -1) < 0 or integer(count) > MAX_QUANTITY:
                    raise SimulationError("INVALID_SAVE", "Item counts must be nonnegative and within the local limit")
            # A local import cannot replace login hashes or another account's identity.
            self._write(username, state)
            return deepcopy(state)

    def gm_catalog(self) -> list[dict]:
        extra=[(name,desc,arg,'testing') for name,desc,arg in [('talentLevel','Set exact talent level (0–330)','115'),('captainLevel','Set captain level independently of Voyage cap','115'),('charactersLevel','Set owned character levels','115'),('maxHaki','Max all elemental Haki slots at captured caps',''),('maxPets','Max owned and unowned captured pets and collections',''),('maxMounts','Max mounts and reins; preserve assignments',''),('maxTreasures','Max treasures and materials',''),('maxShips','Max ships, dock, cabin and charts',''),('maxAllSystems','Max pets, mounts, treasures and ships',''),('bossPractice','Practice a captured boss without progression rewards','{"kind":"tower","id":1}')]]
        return [{"command": name, "description": desc, "exampleArg": arg, "category": category,
                 "capability": "client-action" if category == "client" else "simulated", "offlineOnly": True}
                for name, desc, arg, category in list(GM_COMMANDS)+extra]

    def capabilities(self) -> dict:
        implemented = sorted(self._implemented_ids())
        return {"mode": "offline", "fullGM": True, "gmCommands": self.gm_catalog(), "implementedCommandIds": implemented,
                "initializationStubIds": sorted(self.init_ids - set(implemented)),
                "unsupportedCommandIds": sorted(set(self.commands) - set(implemented) - self.init_ids),
                "fidelity": "Client tables and protocol shapes are recovered; server behavior is a local reimplementation.",
                "multiplayer": "Local NPC simulation only; no remote players, purchases, or live services."}

    def schema_defaults(self, name: str | None, depth=0) -> dict:
        if not name or depth > 8:
            return {}
        result = {}
        for field in self.schemas.get(name, {}).get("fields", []):
            key = field["name"]
            if field.get("repeated"):
                result[key] = []
            elif field.get("required"):
                typ = field.get("type")
                result[key] = self.schema_defaults(field.get("message"), depth + 1) if typ == "message" else "" if typ == "string" else False if typ == "bool" else [] if typ == "bytes" else 0
        return result

    def fill_schema(self, name: str | None, values: dict | None = None, depth=0) -> dict:
        result = self.schema_defaults(name, depth)
        result.update(deepcopy(values or {}))
        if depth > 8:
            return result
        for field in self.schemas.get(name, {}).get("fields", []):
            key = field["name"]
            if field.get("type") != "message" or key not in result:
                continue
            if field.get("repeated"):
                result[key] = [self.fill_schema(field["message"], value, depth + 1) for value in result[key]]
            elif isinstance(result[key], dict):
                result[key] = self.fill_schema(field["message"], result[key], depth + 1)
        return result

    def _reply(self, command_id: int, values: dict | None = None) -> dict:
        return self.fill_schema(self.commands.get(command_id, {}).get("response"), values)

    @staticmethod
    def _costs(value: str) -> list[tuple[int, int]]:
        costs = []
        for entry in (value or "").split("#"):
            if not entry:
                continue
            parts = entry.split("_")
            if len(parts) != 3 or parts[0] != "1":
                raise SimulationError("UNSUPPORTED_COST", f"The local simulator does not implement cost encoding {entry!r}")
            costs.append((integer(parts[1]), integer(parts[2])))
        return costs

    @staticmethod
    def _change_item(state: dict, ref_id: int, amount: int) -> dict:
        current = integer(state["inventory"].get(str(ref_id)))
        value = current + amount
        if value < 0:
            raise SimulationError("INSUFFICIENT_ITEMS", f"Item {ref_id}: need {-amount}, have {current}")
        if value > MAX_QUANTITY:
            raise SimulationError("QUANTITY_LIMIT", f"Local item limit is {MAX_QUANTITY}")
        state["inventory"][str(ref_id)] = value
        return item_vo(ref_id, value)

    def _spend(self, state: dict, encoded: str, multiplier=1) -> list[dict]:
        costs = self._costs(encoded)
        combined = {}
        for ref_id, count in costs:
            combined[ref_id] = combined.get(ref_id, 0) + count * multiplier
        for ref_id, count in combined.items():
            if integer(state["inventory"].get(str(ref_id))) < count:
                name = self.english(self.items.get(ref_id, {}).get("name", str(ref_id)))
                raise SimulationError("INSUFFICIENT_ITEMS", f"Not enough {name}: need {count}, have {state['inventory'].get(str(ref_id), 0)}")
        changed = [self._change_item(state, ref_id, -count) for ref_id, count in combined.items()]
        spent = sum(count for ref_id, count in combined.items() if ref_id in (101, 111))
        if spent:
            counters = state.setdefault("progression", {})
            counters["diamondsSpent"] = integer(counters.get("diamondsSpent")) + spent
        return changed

    def _grant(self, state: dict, encoded: str, multiplier=1) -> list[dict]:
        rewards = self._costs(encoded)
        changed = []
        for ref_id, count in rewards:
            if ref_id not in self.items and ref_id not in self.generals:
                raise SimulationError("UNKNOWN_ITEM", f"Item {ref_id} is absent from the captured reference set")
            if ref_id in self.equips:
                amount=count*multiplier
                if not 0<=amount<=10000:raise SimulationError('INVALID_GEAR_COUNT','Grant at most 10,000 equipment pieces per action.')
                sequence=max([integer(e['equipId'])-8800000000000 for e in state['equipment']]+[0])+1
                added=[self._equip_vo(ref_id,sequence+i) for i in range(amount)]
                state['equipment'].extend(added)
                state.setdefault('_pendingBroadcasts',[]).append({'id':1353,'data':{'equips':added}})
            else:self._change_item(state, ref_id, count * multiplier)
            changed.append(item_vo(ref_id, count * multiplier))
        return changed

    def _general_vo(self, gid: int, level: int, star: int, selected=False) -> dict:
        row = self.generals.get(gid, {})
        eligible = [skill for skill in self.general_skills.get(gid, []) if integer(skill.get("type")) == 1 and integer(skill.get("lock")) <= level and integer(skill.get("generalType")) == 0]
        chosen = max(eligible, key=lambda skill: integer(skill.get("lock")), default={})
        skill_list = chosen.get("skillId", row.get("skillList", ""))
        return {"generalId": gid, "level": level, "star": star, "isSelect": selected, "devilFruit": 0,
                "skillIds": [integer(value) for value in skill_list.split("#") if value],
                "attrs": [], "rule": 1, "equipType": 0, "entryInfos": [], "skinId": 0, "footprintId": 0, "skillSkins": [], "mountId": 0}

    def _equip_vo(self, ref_id: int, sequence: int) -> dict:
        row=self.equips.get(ref_id,{})
        rolls=self.equipment_rules.rolls(row) if hasattr(self,'equipment_rules') and not integer(row.get('needAuth')) else []
        return {"equipId": str(8800000000000 + sequence), "equipRefId": ref_id, "generalId": 0, "randomAttrRefIds": rolls, "lock": False}

    def _general(self, state: dict, gid: int) -> dict:
        general = state["generals"].get(str(gid))
        if general is None:
            raise SimulationError("CHARACTER_NOT_OWNED", f"Character {gid} is not in this local roster")
        return general

    def _attrs(self, state: dict, general: dict) -> list[dict]:
        return self.stats.evaluate(state)[str(general["generalId"])]["attrs"]

    def _roster(self, state: dict) -> list[dict]:
        result = deepcopy(list(state["generals"].values()))
        calculated = self.stats.evaluate(state)
        for general in result:
            general["attrs"] = calculated[str(general["generalId"])]["attrs"]
            fruit_skills={integer(r['skill']) for r in self.systems.fruits.values()}
            general['skillIds']=[skill for skill in general.get('skillIds',[]) if skill not in fruit_skills]
            fruit=self.systems.fruits.get(integer(general.get('devilFruit')))
            if fruit and integer(fruit.get('skill')):general['skillIds'].append(integer(fruit['skill']))
            skin = self.general_skins.get(integer(general.get("skinId")), {})
            existing = {entry["refId"] for entry in general.get("entryInfos", [])}
            entries = skin.get("entry", "").split("#") + self.equipment_rules.entries(state, general['generalId'])
            for ref_id in entries:
                if integer(ref_id) and integer(ref_id) not in existing:
                    general.setdefault("entryInfos", []).append({"refId": integer(ref_id), "count": 1})
        return result

    def _sync_player_attrs(self, state: dict):
        totals = {"attack": 0, "hp": 0, "power": 0}
        calculated = self.stats.evaluate(state)
        for general in state['generals'].values():
            if general.get("isSelect"):
                for attr in calculated[str(general['generalId'])]['attrs']:
                    if attr["key"] in totals:
                        totals[attr["key"]] += attr.get("doubleValue", 0)
        state["player"]["attrs"] = [{"attrType": key, "attrValue": totals[name]} for key, name in [(1, "attack"), (2, "hp"), (1000, "power")]]

    @staticmethod
    def _mail(sequence: int, title: str, content: str, attachment: str) -> dict:
        stamp = now_ms()
        return {"emailId": sequence, "attachment": attachment, "senderId": 0, "sendTime": stamp,
                "expireTime": stamp + 365 * 86400000, "state": 0, "title": title, "content": content,
                "i18n": {"title": {"content": title, "params": []}, "content": {"content": content, "params": []}}}

    @staticmethod
    def _implemented_ids() -> set[int]:
        return {1001, 1006, 1008, 1009, 1010, 1011, 1013, 1019, 1021, 1022, 1024, 1048,
                1100, 1101, 1102, 1103, 1104, 1110, 1300, 1301, 1303, 1304, 1305, 1307, 1313, 1314, 1315, 1316, 1323,
                1200, 1201, 1350, 1351, 1352, 1354, 1355, 1400, 1402, 1410, 1418, 1420, 1701, 1702, 1703, 1704, 1951,
                1801, 1802, 2000, 2501, 2600, 2601, 2605, 2700, 2701, 2702, 2703, 2706, 2707, 2709,
                3600, 3601, 3602, 50001, 50002, 50004, 50005, 50006, 50010, 50013, 50019,
                50101, 50102, 50103, 51001, 51002, 51004, 51005, 51050, 52001, 52002, 52003, 52005, 52007, 52009, 6008, 6700, 6701, 70000, 80000, 90002, 90003} | set(OfflineProgression.handled_ids) | set(OfflineEncounters.handled_ids) | OfflineCompanions.handled_ids | OfflineWorkshop.handled_ids | OfflineEquipment.handled_ids | OfflineVoyage.handled_ids | OfflineSystems.handled_ids | OfflineWorld.handled_ids | OfflineStages.handled_ids

    def command(self, account: str | dict, command_id: int, payload: dict | None = None) -> dict:
        username = self._username(account)
        cid, payload = integer(command_id), payload or {}
        if not isinstance(payload, dict):
            return self._error(cid, "INVALID_PAYLOAD", "Request payload must be an object")
        if cid == 70000:
            return self.gm(username, str(payload.get("command", "")), str(payload.get("arg", "")))
        with self._lock:
            state = self._read(username)
            before_inventory = dict(state["inventory"])
            before_tasks = deepcopy(state["tasks"])
            before_level = state["player"]["level"]
            before_stats = self.stats.signature(state)
            try:
                reply, mutated, capability = self._dispatch(state, cid, payload)
                self._sync_tasks(state)
                broadcasts = state.pop("_pendingBroadcasts", [])
                if mutated:
                    self._write(username, state)
                    changed = [item_vo(integer(ref_id), count) for ref_id, count in state["inventory"].items() if before_inventory.get(ref_id) != count]
                    if changed:
                        broadcasts.append({"id": 1105, "data": {"itemList": changed}})
                    stats_changed = before_stats != self.stats.signature(state)
                    if stats_changed:
                        roster = self._roster(state)
                        broadcasts.append({"id":1007,"data":{"attrs":state['player']['attrs'],"generals":roster}})
                        broadcasts.append({"id":1302,"data":{"generals":roster}})
                    broadcasts.append({'id':2103,'data':{'tasks':self.voyage.info(state)['tasks']}})
                    if cid == 1751:
                        broadcasts.append({"id": 1353, "data": {"equips": reply.get('equips', [])}})
                    if cid == 50102:
                        broadcasts.append({"id": 50105, "data": {"npcIds": self._effective_npc_ids(state), "bossIds": state["unlockedBossIds"]}})
                    if state["tasks"] != before_tasks:
                        broadcasts.append({"id": 1401, "data": {"taskInfos": self._visible_tasks(state)}})
                    if state["player"]["level"] != before_level:
                        broadcasts.append({"id": 1015, "data": {"attrs": [{"key": "level", "type": "int64", "int64Value": state["player"]["level"]}]}})
                return {"ok": True, "revision": state["updatedAt"], "commandId": cid, "reply": self._reply(cid, reply), "broadcasts": broadcasts, "clientAction": {"type": "rebirthAll"} if cid == 50101 else None,
                        "capability": capability, "offlineOnly": True}
            except SimulationError as error:
                return self._error(cid, error.code, error.message)
            except (ValueError, TypeError, KeyError, IndexError) as error:
                return self._error(cid, "INVALID_PARAMETERS", str(error))

    @staticmethod
    def _error(cid: int, code: str, message: str) -> dict:
        return {"ok": False, "commandId": cid, "reply": {}, "broadcasts": [], "capability": "unsupported" if code.startswith("UNSUPPORTED") else "simulated",
                "error": {"code": code, "message": message}, "offlineOnly": True}

    def _dispatch(self, s: dict, cid: int, p: dict) -> tuple[dict, bool, str]:
        if cid in self.stages.handled_ids:
            return self.stages.dispatch(s,cid,p)
        if cid in self.world.handled_ids:
            return self.world.dispatch(s,cid,p)
        if cid in self.systems.handled_ids:
            return self.systems.dispatch(s,cid,p)
        if cid in self.voyage.handled_ids:
            return self.voyage.dispatch(s, cid, p)
        if cid in self.equipment_rules.handled_ids:
            return self.equipment_rules.dispatch(s, cid, p)
        if cid in self.companions.handled_ids:
            return self.companions.dispatch(s, cid, p)
        if cid in self.workshop.handled_ids:
            return self.workshop.dispatch(s, cid, p)
        if cid in self.encounters.handled_ids:
            return self.encounters.dispatch(s, cid, p)
        progression_result = self.progression.dispatch(s, cid, p)
        if progression_result is not None:
            return progression_result
        sim = "simulated"
        if cid == 90002:
            return {"chats": [], "lastReadInfos": []}, False, "local-empty"
        if cid == 90003:
            return {"PrivateChatTabs": []}, False, "local-empty"
        if cid == 1410:
            return {"payInfo": [], "rechargeInfo": []}, False, "local-empty"
        if cid == 1951:
            return {"vos": [], "autoGiveUpFuId": [], "openCount": 0}, False, "local-empty"
        if cid in (1200, 1201):
            daily = s.setdefault("dailySignIn", {"groupId": 1, "days": [], "signCount": 0, "pay": False, "lastDay": ""})
            rewards = []
            if cid == 1201:
                today = time.strftime("%Y-%m-%d", time.gmtime())
                if daily["lastDay"] == today:
                    raise SimulationError("ALREADY_CLAIMED", "Today's local sign-in reward has already been claimed")
                day = len(daily["days"]) + 1
                row = next((r for r in self.table("DaySignInRef") if integer(r["groupId"]) == daily["groupId"] and integer(r["day"]) == day), None)
                if not row:
                    raise SimulationError("NO_SIGN_IN_REWARD", "No further captured sign-in reward in this group")
                rewards = self._grant(s, row["reward"])
                daily["days"].append(day)
                daily["signCount"] += 1
                daily["lastDay"] = today
            return {"info": daily, "reward": rewards}, cid == 1201, sim
        if cid in (6700, 6701):
            onhook = s.setdefault("onhook", {"lastRewardTime": now_ms(), "todayFreeCount": 0, "todayCostCount": 0})
            rewards = []
            if cid == 6701:
                minutes = min(720, max(0, (now_ms() - onhook["lastRewardTime"]) // 60000))
                if minutes:
                    rewards = self._grant(s, f"1_102_{minutes * 10}#1_103_{minutes}")
                    onhook["lastRewardTime"] = now_ms()
            return {**onhook, "curMapId": s["scene"]["mapId"], "rewards": rewards}, cid == 6701, "approximated"
        if cid == 50001:
            scene_id = integer(p.get("refId"), s["scene"]["mapId"])
            if scene_id not in self.scenes:
                raise SimulationError("UNKNOWN_MAP", "Scene is absent from the captured reference tables")
            s["scene"]["mapId"] = scene_id
            visited = s["progression"]["mapsVisited"]
            if scene_id not in visited:
                visited.append(scene_id)
            s["scene"]["createdSprites"] = {}
            s["scene"]["createdLoot"] = {}
            s["scene"]["rewardedSprites"] = []
            return {"sceneData": {"uid": scene_id, "curLayer": 1, "sprites": [], "players": []}, "layer": {"layer": 1, "curCount": 1}}, True, sim
        if cid == 50002:
            return {}, False, sim
        if cid == 50004:
            point = p.get("centerPos") or {}
            before = (s['scene']['x'],s['scene']['y'])
            s["scene"]["x"] = integer(point.get("x"), s["scene"]["x"])
            s["scene"]["y"] = integer(point.get("y"), s["scene"]["y"])
            return {}, before != (s['scene']['x'],s['scene']['y']), sim
        if cid == 50006:
            registry = s["scene"].setdefault("createdSprites", {})
            for sprite in p.get("monsters") or []:
                if str(sprite.get("uid", "")):
                    registry[str(sprite["uid"])] = integer(sprite.get("id"))
            loot_registry = s["scene"].setdefault("createdLoot", {})
            for sprite in p.get("loots") or []:
                if str(sprite.get("uid", "")):
                    loot_registry[str(sprite["uid"])] = integer(sprite.get("id"))
            return {}, bool(p.get("monsters") or p.get("loots")), sim
        if cid == 50005:
            registry = s["scene"].setdefault("createdSprites", {})
            loot_registry = s["scene"].setdefault("createdLoot", {})
            rewarded = set(s["scene"].setdefault("rewardedSprites", []))
            outputs = []
            for dead in p.get("vos") or []:
                uid = str(dead.get("uid", ""))
                if uid in loot_registry and uid not in rewarded:
                    row = self.scene_loot.get(loot_registry[uid])
                    if not row:
                        continue
                    rewards = self._grant(s, row.get("dropItem", ""))
                    rewarded.add(uid)
                    for reward in rewards:
                        ref = str(reward["refId"])
                        gathered = s["progression"]["gathered"]
                        gathered[ref] = integer(gathered.get(ref)) + reward["count"]
                        outputs.append({"uid": integer(uid), "itemRefId": reward["refId"], "number": reward["count"]})
                elif uid in registry and uid not in rewarded:
                    rewarded.add(uid)
                    self._change_item(s, 102, 10)
                    self._change_item(s, 103, 1)
                    kills = s["progression"]["kills"]
                    ref = str(registry[uid])
                    kills[ref] = integer(kills.get(ref)) + 1
                    outputs.append({"uid": integer(uid), "itemRefId": 102, "number": 10})
            s["scene"]["rewardedSprites"] = list(rewarded)
            return {"ops": outputs, "bxs": []}, bool(outputs), "approximated"
        if cid == 50010 and s.get("activeInstance"):
            return self._apply_instance_damage(s, p), True, "approximated"
        if cid in (50010, 50013):
            return {}, False, "client-authoritative-local"
        if cid == 50019:
            return {"hatered": []}, False, "local-empty"
        if cid in (1001, 1006):
            return {"sessionId": f"offline-{s['username']}", "playerId": s["playerId"], "serverTime": now_ms(), "player": s["player"],
                    "serverVersion": "offline", "serverSvnVersion": "offline-simulation", "timeZone": "UTC"}, False, sim
        if cid == 80000:
            return {"serverTime": now_ms()}, False, sim
        if cid == 1008:
            name = str(p.get("nickname", p.get("name", ""))).strip()
            if not name or len(name) > 24:
                raise SimulationError("INVALID_NAME", "Use a nickname of 1–24 characters")
            s["player"]["nickname"] = name
            return {"nickname": name, "changeNameCount": 0}, True, sim
        if cid == 1009:
            s["player"]["level"] += 1
            return {"newLevel": s["player"]["level"], "reward": []}, True, "approximated"
        if cid == 1013:
            s["player"]["desc"] = str(p.get("desc", ""))[:500]
            return {"desc": s["player"]["desc"]}, True, sim
        if cid in (1010, 1021):
            source, key = (s["appends"], "appends") if cid == 1010 else (s["doneValues"], "doneVos")
            return {key: [{"key": key, "value": value} for key, value in source.items()]}, False, sim
        if cid in (1011, 1022):
            entry = p.get("append" if cid == 1011 else "doneVo", {})
            s["appends" if cid == 1011 else "doneValues"][str(entry.get("key", ""))] = entry.get("value", "")
            return {}, True, sim
        if cid == 1019:
            s["settings"]["guide"] = deepcopy(p)
            return {}, True, sim
        if cid == 1024:
            codes = p.get("cmdCodes", p.get("cmdCode", p.get("codes", [])))
            if not isinstance(codes, list):
                codes = [codes]
            entries = []
            for code in codes:
                code = integer(code)
                if code == 1024:
                    continue
                reply, _, _ = self._dispatch(s, code, {})
                entries.append({"cmdCode": code, "data": self._reply(code, reply)})
            return {"data": entries, "_decodedBatch": True}, False, sim
        if cid == 1048:
            ref_id, count = integer(p.get("itemId")), integer(p.get("count"))
            if ref_id not in self.items or count < 0:
                raise SimulationError("INVALID_ITEM", "Select a captured item and nonnegative quantity")
            changed = self._change_item(s, ref_id, count if p.get("isAdd", True) else -count)
            return {"item": changed}, True, sim
        if cid == 1100:
            return {"item": [item_vo(integer(key), value) for key, value in s["inventory"].items()], "records": []}, False, sim
        if cid == 1103:
            ref_id, count = integer(p.get("refId")), integer(p.get("count"), 1)
            if not 1 <= count <= MAX_QUANTITY:
                raise SimulationError("INVALID_COUNT", "Use a positive bounded crafting quantity")
            recipe = next((row for row in self.table("ItemCompoundRef") if integer(row["refId"]) == ref_id), None)
            if not recipe:
                raise SimulationError("UNKNOWN_RECIPE", "No captured recipe for this item")
            self._spend(s, recipe.get("reqGoods", ""), count)
            return {"rewards": self._grant(s, recipe.get("targetGoods", ""), count)}, True, "reference-driven"
        if cid == 1104:
            entries = p.get("split")
            if not isinstance(entries, list) or not 1 <= len(entries) <= 1000:
                raise SimulationError("INVALID_SPLIT", "Select a bounded list of owned gems")
            costs, rewards = {}, {}
            for entry in entries:
                if not isinstance(entry, dict):
                    raise SimulationError("INVALID_SPLIT", "Gem entries must be objects")
                ref_id, count = integer(entry.get("refId")), integer(entry.get("count"))
                if ref_id not in self.progression.gems or not 1 <= count <= MAX_QUANTITY:
                    raise SimulationError("INVALID_SPLIT", "Select an owned gem and a positive bounded quantity")
                price = self.items.get(ref_id, {}).get("price", "")
                if not price:
                    raise SimulationError("UNSUPPORTED_SPLIT", "No captured decomposition return for this gem")
                costs[ref_id] = costs.get(ref_id, 0) + count
                for reward_id, quantity in self._costs(price):
                    rewards[reward_id] = rewards.get(reward_id, 0) + quantity * count
            self._spend(s, "#".join(f"1_{ref_id}_{count}" for ref_id, count in costs.items()))
            return {"rewards": self._grant(s, "#".join(f"1_{ref_id}_{count}" for ref_id, count in rewards.items()))}, True, "reference-driven"
        if cid == 1110:
            ref_id = integer(p.get("refId"))
            return {"item": item_vo(ref_id, integer(s["inventory"].get(str(ref_id))))}, False, sim
        if cid == 1101:
            ref_id, count = integer(p.get("refId")), max(1, integer(p.get("useCount"), 1))
            row = self.items.get(ref_id)
            if not row:
                raise SimulationError("UNKNOWN_ITEM", "Unknown captured item")
            effect = row.get("effect", "")
            if not effect or not re.fullmatch(r"1_\d+_\d+(#1_\d+_\d+)*", effect):
                raise SimulationError("UNSUPPORTED_ITEM_EFFECT", "This item's server-side effect has not been implemented locally; no items were consumed")
            self._spend(s, f"1_{ref_id}_{count}")
            rewards = self._grant(s, effect, count)
            return {"dailyUseCount": count, "rewards": rewards}, True, sim
        if cid == 1102:
            ref_id, count = integer(p.get("refId")), max(1, integer(p.get("count", p.get("saleCount", 1))))
            row = self.items.get(ref_id, {})
            price = row.get("price", "")
            if not price:
                raise SimulationError("UNSUPPORTED_SALE", "No captured sale-price rule; no items were consumed")
            self._spend(s, f"1_{ref_id}_{count}")
            return {"reward": self._grant(s, price, count)}, True, sim
        if cid == 1300:
            roster = self._roster(s)
            slots = [integer(r.get("refId")) for r in self.table("GeneralFightRef") if integer(r.get("type")) == 1]
            selected_count = sum(bool(g["isSelect"]) for g in roster)
            return {"generals": roster, "activeFights": slots[:max(1, selected_count)], "freeResetCount": 99,
                    "skins": list(s["generalSkins"].values()), "echoRefId": 0, "foorprints": [], "skillSkins": [], "petId": s["settings"].get("petAppearId", 0)}, False, sim
        if cid in (1314, 1315, 1316):
            skin_id = integer(p.get("skinId"))
            ref = self.general_skins.get(skin_id)
            if not ref:
                raise SimulationError("UNKNOWN_SKIN", "Select a skin from the captured GeneralSkinRef table")
            owned = s["generalSkins"].get(str(skin_id))
            if cid == 1314:
                if not owned:
                    self._spend(s, ref.get("cost", ""))
                    owned = {"skinId": skin_id, "star": 1}
                    s["generalSkins"][str(skin_id)] = owned
                return {"vo": owned}, True, sim
            if not owned:
                raise SimulationError("SKIN_NOT_OWNED", "Activate the skin first, or use the offline equipSkin GM action")
            if cid == 1315:
                next_star = owned["star"] + 1
                row = next((r for r in self.table("GeneralSkinStarRef") if integer(r.get("skinId")) == skin_id and integer(r.get("star")) == owned["star"]), None)
                if not row or not any(integer(r.get("skinId"))==skin_id and integer(r.get("star"))==next_star for r in self.table("GeneralSkinStarRef")):
                    raise SimulationError("MAX_PROGRESSION", "Maximum captured skin progression reached")
                self._spend(s, row["cost"])
                owned["star"] = next_star
                return {"vo": owned}, True, sim
            general = self._general(s, integer(ref["generalId"]))
            general["skinId"] = skin_id
            return {"general": {**general, "attrs": self._attrs(s, general)}}, True, sim
        if cid in (1301, 1303):
            gid = integer(p.get("generalId"))
            general = self._general(s, gid)
            key, rows = ("level", self.general_levels) if cid == 1301 else ("star", self.general_stars)
            current = general[key]
            row = rows.get((gid, current))
            next_row = rows.get((gid, current + 1))
            if not row or not next_row:
                raise SimulationError("MAX_PROGRESSION", "Maximum captured progression reached")
            if cid == 1301 and integer(next_row.get("star")) > general["star"]:
                raise SimulationError("STAR_REQUIRED", "Upgrade this character's star before increasing level")
            self._spend(s, row.get("cost", ""))
            general[key] += 1
            reply_general = deepcopy(general)
            reply_general["attrs"] = self._attrs(s, general)
            return {"general": reply_general, "echoRefId": self.systems.echo(s)}, True, sim
        if cid in (1304, 1305, 1307):
            gid = integer(p.get("generalId"))
            if str(gid) not in s["generals"]:
                if gid not in self.generals:
                    raise SimulationError("UNKNOWN_CHARACTER", "Unknown captured character")
                self._spend(s, f"1_{gid}_1")
                s["generals"][str(gid)] = self._general_vo(gid, 1, 0)
            general = s["generals"][str(gid)]
            general["isSelect"] = cid != 1305
            return {"generals": self._roster(s), "reward": [], "equips": s["equipment"], "echoRefId": self.systems.echo(s)}, True, "approximated"
        if cid == 1313:
            gid = integer(p.get("generalId"))
            general = self._general(s, gid)
            refund = {}
            for level in range(1, general["level"]):
                for ref_id, count in self._costs(self.general_levels.get((gid, level), {}).get("cost", "")):
                    refund[ref_id] = refund.get(ref_id, 0) + count
            for ref_id, count in refund.items():
                self._change_item(s, ref_id, count)
            general["level"] = 1
            return {"general": general, "rewards": [item_vo(ref_id, count) for ref_id, count in refund.items()]}, True, "approximated"
        if cid == 1323:
            general = self._general(s, integer(p.get("generalId")))
            return {"displayAttrs": self._attrs(s, general), "sysDisPlay": []}, False, "approximated"
        if cid == 1350:
            return {"equips": s["equipment"]}, False, sim
        if cid in (1351, 1352, 1355):
            equip = next((e for e in s["equipment"] if e["equipId"] == str(p.get("equipId"))), None)
            if not equip:
                raise SimulationError("UNKNOWN_EQUIPMENT", "Select an owned offline equipment ID")
            if cid == 1351:
                gid = integer(p.get("generalId"))
                self._general(s, gid)
                row = self.equips.get(equip["equipRefId"], {})
                for other in s["equipment"]:
                    if other.get("generalId") == gid and self.equips.get(other["equipRefId"], {}).get("part") == row.get("part"):
                        other["generalId"] = 0
                equip["generalId"] = gid
            elif cid == 1352:
                equip["generalId"] = 0
            else:
                equip["lock"] = bool(p.get("lock", not equip["lock"]))
            return {"equips": s["equipment"], "equip": equip}, True, sim
        if cid == 1354:
            ids = p.get("equipIds", [p.get("equipId")])
            removing = [e for e in s["equipment"] if e["equipId"] in ids and not e["lock"] and not e["generalId"]]
            if not removing:
                raise SimulationError("NO_EQUIPMENT", "No unlocked unequipped items selected")
            s["equipment"] = [e for e in s["equipment"] if e not in removing]
            self._change_item(s, 102, len(removing) * 100)
            return {"equipIds": [e["equipId"] for e in removing], "reward": [item_vo(102, len(removing) * 100)]}, True, "approximated"
        if cid == 1400:
            return {"taskInfos": self._visible_tasks(s), "activeRewardInfos": [], "finishMapBigIds": []}, False, sim
        if cid == 1402:
            task = next((t for t in s["tasks"] if t["refId"] == integer(p.get("refId")) and t["type"] == integer(p.get("type"), 2)), None)
            if not task or task["state"] != 2:
                raise SimulationError("REWARD_NOT_READY", "Complete the local task before claiming its reward")
            rewards = self._grant(s, self.task_refs.get(task["refId"], {}).get("reward", "1_102_10"))
            task["state"] = 3
            self._activate_next_task(s, task["refId"])
            self._advance_player_level(s)
            return {"reward": rewards}, True, sim
        if cid == 1420:
            task = next((t for t in self._visible_tasks(s) if t["refId"] == integer(p.get("refId"))), None)
            if not task or self.task_refs.get(task["refId"], {}).get("finishCondition", "").split("_")[0] not in ("4", "34", "51"):
                raise SimulationError("TASK_EVENT_REQUIRED", "This task advances through its world action, not a manual count request")
            task["progress"] += 1
            return {}, True, sim
        if cid in (1418, 6008):
            ref_id = integer(p.get("refId", p.get("taskRefId")))
            self._complete_task(s, ref_id)
            return {}, True, sim
        if cid == 1701:
            return {"email": s["mail"]}, False, sim
        if cid in (1702, 1703, 1704):
            email_id = integer(p.get("emailId"))
            mails = [mail for mail in s["mail"] if not email_id or mail["emailId"] == email_id]
            if not mails:
                raise SimulationError("UNKNOWN_MAIL", "No matching local mail")
            rewards, received = [], []
            for mail in mails:
                if cid == 1702:
                    mail["read"] = True
                elif cid == 1703 and mail["state"] != 2:
                    rewards += self._grant(s, mail["attachment"])
                    received.append(mail["emailId"])
                    mail["state"] = 2
                elif cid == 1704:
                    if mail["attachment"] and mail["state"] != 2:
                        raise SimulationError("UNCLAIMED_MAIL", "Claim this attachment before deleting the mail")
                    s["mail"].remove(mail)
            return {"receiveIds": received, "reward": rewards, "emailIds": [m["emailId"] for m in mails]}, True, sim
        if cid == 1801:
            shops = []
            for row in self.table("ShopRef"):
                shop_id = integer(row.get("id"))
                shops.append({"shopId": shop_id, "item": [{"refId": item_id, "purchaseTimes": integer(s["shopPurchases"].get(str(item_id))), "discount": 100, "onSaleTime": 0}
                             for item_id, item in self.shop_items.items() if integer(item.get("shopId")) == shop_id]})
            return {"shops": shops}, False, sim
        if cid == 1802:
            item_id, count = integer(p.get("shopItemRefId")), max(1, integer(p.get("count"), 1))
            row = self.shop_items.get(item_id)
            if not row or integer(row.get("shopId")) != integer(p.get("shopId")):
                raise SimulationError("UNKNOWN_SHOP_ITEM", "Select a captured item from this shop")
            if row.get("productId") not in (None, "", "0"):
                raise SimulationError("UNSUPPORTED_PURCHASE", "Real-money purchases are disabled in offline mode; use GM item grants")
            self._spend(s, row.get("price", ""), count)
            rewards = self._grant(s, row.get("item", ""), count)
            s["shopPurchases"][str(item_id)] = integer(s["shopPurchases"].get(str(item_id))) + count
            return {"shopId": integer(row["shopId"]), "item": {"refId": item_id, "purchaseTimes": s["shopPurchases"][str(item_id)], "discount": 100}, "reward": rewards}, True, "approximated"
        if cid == 2000:
            floors = self.table("TowerLevelRef")
            floor_ids = [integer(row.get("refId")) for row in floors]
            floor_id = floor_ids[min(s["towerFloor"] - 1, len(floor_ids) - 1)] if floor_ids else 1
            return {"info": {"refId": floor_id, "floor": s["towerFloor"], "generalIds": [g["generalId"] for g in s["generals"].values() if g["isSelect"]], "rankReward": False, "processIds": []}}, False, sim
        if cid == 2501:
            ids = [value for value in s["player"]["personality"].values() if value]
            return {"infos": [{"refId": ref_id, "endTime": 4102444800000, "activeFlag": True} for ref_id in ids]}, False, sim
        if cid == 3600:
            return {"infos": [{"refId": integer(key), "lv": value} for key, value in s["potential"].items()]}, False, sim
        if cid in (3601, 3602):
            ref_id = integer(p.get("refId"))
            current = integer(s["potential"].get(str(ref_id)))
            if cid == 3602:
                s["potential"].clear()
                return {"infos": []}, True, "approximated"
            row = self.potential_levels.get((ref_id, current + 1))
            if not row:
                raise SimulationError("MAX_POTENTIAL", "No next captured potential level")
            self._spend(s, row.get("cost", ""))
            s["potential"][str(ref_id)] = current + 1
            return {"info": {"refId": ref_id, "lv": current + 1}}, True, sim
        if cid == 50101:
            if not p.get("free"):
                self._spend(s, self.global_config.get("rebirthCost", "1_101_20"))
            s["scene"]["dead"] = False
            return {}, True, sim
        if cid == 50102:
            npc_id = integer(p.get("npcId"))
            npc = self.npcs.get(npc_id)
            if not npc:
                raise SimulationError("UNKNOWN_NPC", "NPC is absent from the captured map data")
            if npc_id in s["unlockedNpcIds"]:
                return {"npcId": [npc_id]}, False, sim
            self._spend(s, npc.get("cost", ""))
            rewards = self._grant(s, npc.get("reward", ""))
            s["unlockedNpcIds"].append(npc_id)
            for reward in rewards:
                gid = reward["refId"]
                if integer(npc.get("type")) == 3 and gid in self.generals and str(gid) not in s["generals"]:
                    selected = sum(g.get("isSelect", False) for g in s["generals"].values()) < 3
                    s["generals"][str(gid)] = self._general_vo(gid, 1, 0, selected)
            if integer(npc.get("bossId")):
                s["unlockedBossIds"].append(integer(npc["bossId"]))
            return {"npcId": [npc_id]}, True, sim
        if cid == 50103:
            return {"npcIds": self._effective_npc_ids(s), "bossIds": s["unlockedBossIds"]}, False, sim
        if cid in (52001, 52009):
            boss_type = integer(p.get("type"))
            saved = s.get("bounties", {})
            for boss in saved.values():
                if boss.get("nextRefreshTime") and boss["nextRefreshTime"] <= now_ms():
                    boss.update(hpRate=10000, nextRefreshTime=0)
            infos = [{"subActivityId": key, "hpRate": saved.get(key, {}).get("hpRate", 10000), "nextRefreshTime": saved.get(key, {}).get("nextRefreshTime", 0),
                      "innerCount": saved.get(key, {}).get("innerCount", 0), "enterIds": [], "unlocked": True}
                     for key, row in self.boss_subs.items() if not boss_type or integer(row.get("type")) == boss_type]
            return {"infos": infos, "serverId": []}, False, "simulated"
        if cid == 52002:
            sub_id = str(p.get("subActivityId", ""))
            sub = self.boss_subs.get(sub_id)
            if not sub:
                raise SimulationError("UNKNOWN_BOUNTY", "Bounty is absent from the captured reference tables")
            day = integer(s["settings"].get("serverAgeDays"), 365)
            ref = next((r for r in self.table("WorldBossInsRef") if integer(r["groupId"]) == integer(sub["insGroup"]) and (integer(r["startDay"]) < 0 or integer(r["startDay"]) <= day) and (integer(r["endDay"]) < 0 or integer(r["endDay"]) >= day)), None)
            if not ref:
                raise SimulationError("NO_BOUNTY_INSTANCE", "No captured bounty instance matches this simulated server age")
            self._spend(s, sub.get("cost", ""))
            data = self._make_instance(s, integer(ref["insId"]), 1, p.get("generals") or [])
            s["activeInstance"].update(subId=sub_id, bountyRef=ref)
            boss = s.setdefault("bounties", {}).setdefault(sub_id, {"hpRate": 10000, "innerCount": 0})
            boss["innerCount"] += 1
            return {"data": data, "desc": self._scene_player(s)}, True, "approximated"
        if cid == 52003:
            sub_id = str(p.get("subActivityId", ""))
            active = s.get("activeInstance")
            damage = active.get("damage", 0) if active and active.get("subId") == sub_id else 0
            boss = s.get("bounties", {}).get(sub_id, {})
            s.pop("activeInstance", None)
            return {"info": {"subActivityId": sub_id, "hpRate": boss.get("hpRate", 10000), "innerCount": boss.get("innerCount", 0), "nextRefreshTime": boss.get("nextRefreshTime", 0), "enterIds": [], "unlocked": True}, "totalDamage": damage, "curDamage": damage, "times": 1, "subActivityId": sub_id, "type": 1, "rebirthTime": 0}, True, "approximated"
        if cid in (52005, 52007):
            return {"ranks": [], "records": []}, False, "local-empty"
        if cid == 51002:
            ref_id, lv = integer(p.get("refId")), max(1, integer(p.get("lv"), 1))
            ref = self.instances.get(ref_id)
            if not ref:
                raise SimulationError("UNKNOWN_INSTANCE", "Instance is absent from the captured tables")
            self._spend(s, ref.get("cost", ""))
            return {"data": self._make_instance(s, ref_id, lv, p.get("generals") or [])}, True, "approximated"
        if cid == 51005:
            active = self._active_instance(s, p.get("uid"))
            active["data"]["startTime"] = now_ms()
            s.setdefault("_pendingBroadcasts", []).append({"id": 51006, "data": {"uid": active["data"]["uid"], "startTime": active["data"]["startTime"], "playerId": s["playerId"]}})
            return {}, True, "approximated"
        if cid == 51004:
            active = self._active_instance(s, p.get("uid"))
            victory = all(sprite["labile"]["hp"]["cur"] <= 0 for sprite in active["data"]["sprites"] if sprite["type"] == 2)
            if victory:
                self._finish_instance(s, active)
            return {"data": active["data"], "success": victory, "infos": {"refId": active["data"]["refId"], "lv": s["instanceLevels"].get(str(active["data"]["refId"]), active["data"]["lv"])}}, True, "approximated"
        if cid == 51001:
            return {"infos": [{"refId": integer(key), "lv": value} for key, value in s["instanceLevels"].items()]}, False, sim
        if cid == 51050:
            ref_id, level = integer(p.get("refId")), max(1, integer(p.get("lv"), 1))
            s["instanceLevels"][str(ref_id)] = level
            return {"infos": {"refId": ref_id, "lv": level}}, True, sim
        if cid in self.init_ids:
            return self._reply(cid), False, "initialization-stub"
        raise SimulationError("UNSUPPORTED_OFFLINE", f"Command {cid} ({self.commands.get(cid, {}).get('name', 'unknown')}) has no implemented local handler; no state was changed")

    def _scene_player(self, state: dict):
        player = state["player"]
        return {"playerId": state["playerId"], "name": player["nickname"], "lv": player["level"], "vipLv": player["vipLevel"], "personality": player["personality"], "serverId": 1, "campId": state["playerId"]}

    def _active_instance(self, state: dict, uid):
        active = state.get("activeInstance")
        if not active or integer(uid) != active["data"]["uid"]:
            raise SimulationError("NO_ACTIVE_INSTANCE", "This offline instance is no longer active")
        return active

    def _make_instance(self, state: dict, ref_id: int, level: int, generals: list) -> dict:
        ref = self.instance_refs.get((ref_id, level))
        if not ref:
            raise SimulationError("NO_INSTANCE_LEVEL", "No captured configuration for this instance level")
        scene = self.scenes.get(integer(ref["sceneId"]), {})
        birth = scene.get("birthPos", "1792_1600").split("_")
        base_x, base_y = integer(birth[0]), integer(birth[-1])
        uid, sprites = now_ms() * 100, []
        chosen = generals or [g["generalId"] for g in self._roster(state) if g["isSelect"]]
        for n, candidate in enumerate(chosen[:10]):
            if isinstance(candidate, dict):
                sprite = deepcopy(candidate)
                sprite.update(type=1, playerId=state["playerId"], campId=state["playerId"])
                sprites.append(sprite)
                continue
            gid = integer(candidate)
            general = self._general(state, gid)
            attrs = self._attrs(state, general)
            numbers = {a["key"]: a["doubleValue"] for a in attrs}
            actor_uid = uid + n + 1
            point = {"x": base_x + n * 70, "y": base_y, "dir": 0}
            sprites.append({"uid": actor_uid, "id": gid, "type": 1, "labile": {"uid": actor_uid, "pos": point, "hp": {"max": numbers["hp"], "cur": numbers["hp"], "shield": 0}}, "attrs": [{"key": key, "value": numbers[name]} for key, name in [(1, "attack"), (2, "hp"), (38, "speed")]], "skillList": general["skillIds"], "playerId": state["playerId"], "campId": state["playerId"], "skinId": general["skinId"], "brithPos": point})
        waves = self.instance_waves.get(integer(ref.get("refreshConfig")), [])
        for wave in waves:
            for encoded in wave["data"].split("#"):
                bits = encoded.split("_")
                if len(bits) < 4:
                    continue
                monster_id, count, x, y = map(integer, bits[:4])
                monster = self.monsters.get(monster_id)
                if not monster:
                    continue
                attrs = [{"key": integer(a.split("_")[0]), "value": float(a.split("_")[1])} for a in monster.get("attrs", "").split("#") if len(a.split("_")) >= 2]
                hp = next((a["value"] for a in attrs if a["key"] == 2), 1000)
                for n in range(min(50, max(1, count))):
                    sprite_uid = uid + 100 + len(sprites)
                    point = {"x": x + n * 40, "y": y, "dir": 180}
                    sprites.append({"uid": sprite_uid, "id": monster_id, "type": 2, "attrs": attrs, "skillList": [integer(v) for v in monster.get("skill", "").split("#") if v], "labile": {"uid": sprite_uid, "pos": point, "hp": {"max": integer(hp), "cur": integer(hp), "shield": 0}}, "campId": 2, "brithPos": point})
        if not any(sprite["type"] == 2 for sprite in sprites):
            raise SimulationError("UNSUPPORTED_INSTANCE_WAVES", "This instance needs a special encounter handler; no entry cost was saved")
        data = {"uid": uid, "refId": ref_id, "lv": level, "sprites": sprites, "rewards": [], "startTime": now_ms(), "players": [self._scene_player(state)]}
        state["activeInstance"] = {"data": data, "settled": False, "damage": 0}
        return data

    def _apply_instance_damage(self, state: dict, payload: dict):
        active = state["activeInstance"]
        sprites = {str(sprite["uid"]): sprite for sprite in active["data"]["sprites"]}
        pushes = []
        for supplied in payload.get("vo") or []:
            target = sprites.get(str(supplied.get("tarSpriteId")))
            if not target or active["settled"]:
                continue
            info = target["labile"]["hp"]
            damage = max(0, float(supplied.get("damage") or supplied.get("atk") or supplied.get("baseAtk") or 1))
            actual = min(info["cur"], integer(damage))
            info["cur"] = max(0, info["cur"] - actual)
            if target["type"] == 2:
                active["damage"] += actual
            vo = {**supplied, "damage": actual, "dead": info["cur"] == 0}
            pushes.append({"vo": vo, "labile": deepcopy(target["labile"]), "playerId": [state["playerId"]]})
        if pushes:
            state.setdefault("_pendingBroadcasts", []).append({"id": 50011, "data": {"vo": pushes}})
        if all(sprite["labile"]["hp"]["cur"] <= 0 for sprite in active["data"]["sprites"] if sprite["type"] == 2):
            self._finish_instance(state, active)
        return {}

    def _finish_instance(self, state: dict, active: dict):
        if active["settled"]:
            return
        data = active["data"]
        row = self.instance_refs[(data["refId"], data["lv"])]
        encoded = active.get("bountyRef", {}).get("dropReward") or row.get("reward", "")
        flat = "#".join(part for part in encoded.split("#") if part.startswith("1_") and len(part.split("_")) == 3 and integer(part.split("_")[1]) in self.items)
        rewards = self._grant(state, flat)
        data["rewards"] = rewards
        active["settled"] = True
        state["instanceLevels"][str(data["refId"])] = max(data["lv"] + 1, state["instanceLevels"].get(str(data["refId"]), 1))
        pending = state.setdefault("_pendingBroadcasts", [])
        if active.get("subId"):
            sub_id = active["subId"]
            state["bounties"][sub_id].update(hpRate=0, nextRefreshTime=now_ms() + 60_000)
            pending.append({"id": 52004, "data": {"subActivityId": sub_id, "rank": 1, "damage": active["damage"], "reward": rewards, "rebirthTime": 60, "playerId": state["playerId"], "times": 1}})
        else:
            pending.append({"id": 51003, "data": {"data": data, "success": True, "infos": {"refId": data["refId"], "lv": state["instanceLevels"][str(data["refId"])]}}})

    def _effective_npc_ids(self, state: dict) -> list[int]:
        ids = set(state["unlockedNpcIds"])
        if state["settings"].get("freeRoam", True):
            ids.update(integer(row["npcId"]) for row in self.table("SceneRegionRef") if 0 < integer(row["sceneId"]) < 100 and integer(row["npcId"]))
            ids.update(nid for nid, row in self.npcs.items() if 0 < integer(row["sceneId"]) < 100 and integer(row["type"]) in (1, 2, 5, 6, 7))
            for row in self.table("SceneTransferRef"):
                if 0 < integer(row["sceneId"]) < 100:
                    ids.update(integer(row[key]) for key in ("npcId", "npcId1") if integer(row.get(key)))
        return sorted(ids)

    def _activate_next_task(self, state: dict, ref_id: int):
        next_id = integer(self.task_refs.get(ref_id, {}).get("nextTask"))
        if next_id and next_id in self.task_refs and not any(t["refId"] == next_id and t["type"] == 2 for t in state["tasks"]):
            state["tasks"].append({"type": 2, "refId": next_id, "state": 1, "progress": 0, "extInfo": ""})

    def _visible_tasks(self, state: dict) -> list[dict]:
        claimed = {t["refId"] for t in state["tasks"] if t["type"] == 2 and t["state"] == 3}
        return [t for t in state["tasks"] if t["type"] != 2 or not integer(self.task_refs.get(t["refId"], {}).get("preTask")) or integer(self.task_refs.get(t["refId"], {}).get("preTask")) in claimed or t["state"] == 3]

    def _sync_tasks(self, state: dict):
        if "progression" not in state:
            return
        for task in list(state["tasks"]):
            if task["type"] == 2 and task["state"] == 3:
                self._activate_next_task(state, task["refId"])
        for task in self._visible_tasks(state):
            if task["type"] != 2 or task["state"] == 3:
                continue
            row = self.task_refs.get(task["refId"], {})
            parts = row.get("finishCondition", "").split("_")
            kind, target = integer(parts[0]), integer(parts[2]) if len(parts) > 2 else 0
            progress = task["progress"]
            if kind == 3:
                progress = integer(state["progression"]["kills"].get(str(target)))
            elif kind in (2, 31):
                progress = int(target in state["unlockedNpcIds"])
            elif kind == 9:
                progress = integer(state["progression"]["gathered"].get(str(target)))
            elif kind == 15:
                progress = sum(integer(self.npcs.get(nid, {}).get("type")) == 2 for nid in state["unlockedNpcIds"])
            elif kind == 23:
                progress = int(target in state["progression"]["mapsVisited"])
            elif kind == 1:
                progress = state["player"]["level"]
            limit = max(1, integer(row.get("count"), 1))
            task["progress"] = min(limit, max(task["progress"], progress))
            if task["progress"] >= limit:
                task["state"] = 2

    def _advance_player_level(self, state: dict):
        # Player EXP is a cumulative captured item; it is not consumed per level.
        exp = integer(state["inventory"].get("106"))
        while True:
            level = state["player"]["level"]
            if level>=self.voyage.max_level(state):break
            row = self.player_levels.get(level)
            costs = self._costs(row.get("exp", "")) if row else []
            if not costs or exp < costs[0][1] or level + 1 not in self.player_levels:
                break
            state["player"]["level"] += 1

    def english(self, value: str) -> str:
        return english(value)

    def _complete_task(self, state: dict, ref_id: int):
        row = self.task_refs.get(ref_id, {})
        task = next((value for value in state["tasks"] if value["refId"] == ref_id), None)
        if task is None:
            task = {"type": 2, "refId": ref_id, "state": 2, "progress": integer(row.get("count"), 1), "extInfo": ""}
            state["tasks"].append(task)
        task.update(state=2, progress=integer(row.get("count"), 1))

    def gm(self, account: str | dict, command: str, arg: str = "") -> dict:
        username = self._username(account)
        command, arg = command.strip(), str(arg or "")
        if ":" in command and not arg:
            command, arg = command.split(":", 1)
        with self._lock:
            state = self._read(username)
            inventory_before = dict(state["inventory"])
            try:
                detail, action = self._gm_dispatch(state, command, arg)
                if action:
                    state["clientActions"].append({**action, "at": now_ms()})
                    state["clientActions"] = state["clientActions"][-100:]
                pending=state.pop('_pendingBroadcasts',[])
                self._write(username, state)
                changed = [item_vo(integer(key), value) for key, value in state["inventory"].items() if inventory_before.get(key) != value]
                broadcasts = pending+[{"id": 1007, "data": {"attrs": state["player"]["attrs"], "generals": self._roster(state)}}]
                if command in ("level","captainLevel"):
                    broadcasts.append({"id": 1015, "data": {"attrs": [{"key": "level", "type": "int64", "int64Value": state["player"]["level"]}]}})
                if command == "openAllFunc":
                    broadcasts.append({"id": 1004, "data": {"refIds": state["player"]["funcOpenRefIds"]}})
                if changed:
                    broadcasts.append({"id": 1105, "data": {"itemList": changed}})
                if command in ("generalMax", "potentialAll", "equipSkin", "talentAll", "talentLevel", "charactersLevel", "captainLevel", "maxPets", "maxMounts", "maxTreasures", "maxShips", "maxHaki", "maxAllSystems"):
                    broadcasts.append({"id": 1302, "data": {"generals": self._roster(state)}})
                return {"ok": True, "revision": state["updatedAt"], "commandId": 70000, "reply": self._reply(70000), "broadcasts": broadcasts,
                        "capability": "client-action" if action and command in ("actorSpine", "monsterSpine", "TrajectorySpine", "hide", "LayaGC") else "simulated",
                        "message": detail, "clientAction": action, "offlineOnly": True,
                        "playerLevel": state["player"]["level"]}
            except SimulationError as error:
                return self._error(70000, error.code, error.message)
            except (TypeError, ValueError, IndexError, KeyError) as error:
                return self._error(70000, "INVALID_PARAMETERS", str(error))

    def _gm_dispatch(self, s: dict, command: str, arg: str) -> tuple[str, dict | None]:
        from offline_testing import apply
        testing=apply(self,s,command,arg)
        if testing is not None:return testing
        if command=='talentAll':
            s['talent']={'refIds':sorted(self.progression.talents),'advanceIds':sorted(self.progression.advanced_talents)}
            return 'All captured normal and advanced talents are active in this offline save.',{'type':'talentAll'}
        if command=='completeVoyageTasks':
            self.voyage.complete_test_tasks(s)
            return 'Current One Piece objectives are ready to claim; open Voyage to claim rewards and upgrade.',None
        if command == 'addEquip':
            parts=arg.split('_');rid=integer(parts[0]);count=integer(parts[1],1) if len(parts)>1 else 1
            if rid not in self.equips or not 1<=count<=100:
                raise SimulationError('INVALID_GEAR_GRANT','Use a captured EquipRef ID and 1–100 pieces, e.g. 11011_1.')
            sequence=max([integer(e['equipId'])-8800000000000 for e in s['equipment']]+[0])+1
            s['equipment'].extend(self._equip_vo(rid,sequence+i) for i in range(count))
            return f'Created {count} actual gear pieces of reference {rid}.',None
        if command == "stockTestItems":
            self._stock_test_items(s)
            return "Test supplies restocked. Your upgrades and selections are unchanged.", None
        if command == "freeRoam":
            enabled = str(arg).strip().lower() not in ("0", "false", "off")
            s["settings"]["freeRoam"] = enabled
            return "Free exploration " + ("enabled" if enabled else "disabled"), {"type": "freeRoam", "enabled": enabled}
        if command == "equipSkin":
            skin_id = integer(arg)
            skin = self.general_skins.get(skin_id)
            if not skin:
                raise SimulationError("UNKNOWN_SKIN", "Choose a captured skin ID")
            gid = integer(skin["generalId"])
            general = s["generals"].setdefault(str(gid), self._general_vo(gid, 1, 0, True))
            s["generalSkins"].setdefault(str(skin_id), {"skinId": skin_id, "star": 0})
            general["skinId"] = skin_id
            general["isSelect"] = True
            return f"Equipped skin {skin_id} on character {gid} in the local crew", {"type": "equipSkin", "skinId": skin_id, "generalId": gid}
        if command == "serverAge":
            days = integer(arg, -1)
            if not 0 <= days <= 10000:
                raise SimulationError("INVALID_SERVER_AGE", "Use a server age from 0 to 10000 days")
            opened = now_ms() - days * 86400000
            s["player"]["openServerTime"] = opened
            s["settings"]["serverAgeDays"] = days
            return f"Simulated server age set to {days} days", {"type": "serverAge", "days": days, "openServerTime": opened}
        if command in ("addItem", "subItem"):
            entries = self._costs(arg)
            if not entries:
                raise SimulationError("INVALID_PARAMETERS", "Use item triples, for example 1_102_100")
            for ref_id, count in entries:
                if ref_id not in self.items and ref_id not in self.generals:
                    raise SimulationError("UNKNOWN_ITEM", f"Item {ref_id} is absent from captured tables")
                if count < 0 or count > MAX_QUANTITY:
                    raise SimulationError("QUANTITY_LIMIT", "Use a nonnegative quantity within the local item limit")
            for ref_id, count in entries:
                if ref_id in self.equips:
                    if command=='addItem':self._grant(s,f'1_{ref_id}_{count}')
                    else:
                        removable=[e for e in s['equipment'] if e['equipRefId']==ref_id and not e.get('generalId') and not e.get('lock')][:count]
                        ids={e['equipId'] for e in removable};s['equipment']=[e for e in s['equipment'] if e['equipId'] not in ids]
                else:self._change_item(s, ref_id, count if command == "addItem" else -min(count, integer(s["inventory"].get(str(ref_id)))))
            return f"{command}: changed {len(entries)} local item entries", None
        if command == "level":
            level = integer(arg, -1)
            if not 1 <= level <= 10000:
                raise SimulationError("INVALID_LEVEL", "Use a local player level from 1 to 10000")
            s["player"]["level"] = level
            return f"Local player level set to {level}", {"type": "playerLevel", "level": level}
        if command == "generalMax":
            for gid in self.generals:
                max_level = max((level for g, level in self.general_levels if g == gid), default=1)
                max_star = max((star for g, star in self.general_stars if g == gid), default=0)
                general = self._general_vo(gid, max_level, max_star, selected=(str(gid) in s["generals"] and s["generals"][str(gid)]["isSelect"]))
                old=s['generals'].get(str(gid),{})
                for key in ('devilFruit','skinId','footprintId','mountId','rule','equipType'):general[key]=old.get(key,general.get(key,0))
                s["generals"][str(gid)] = general
            return f"All {len(s['generals'])} captured characters are owned at captured maximum level and star", {"type": "refreshRoster"}
        if command == "potentialAll":
            for ref_id in self.potentials:
                s["potential"][str(ref_id)] = max((level for ref, level in self.potential_levels if ref == ref_id), default=1)
            return f"Maxed {len(s['potential'])} captured potential nodes", {"type": "refreshPotential"}
        if command == "openAllFunc":
            s["player"]["funcOpenRefIds"] = sorted(self.functions)
            s["settings"]["allFunctionsOpen"] = True
            return f"Unlocked {len(self.functions)} captured functions locally", {"type": "unlockFunctions", "ids": sorted(self.functions)}
        if command == "mapTransfer":
            parts = arg.split("#")
            map_id = integer(parts[0], -1)
            if map_id not in self.scenes:
                raise SimulationError("UNKNOWN_MAP", "Select a scene ID present in SceneRef; the template's 999 may not exist")
            scene = self.scenes[map_id]
            birth = scene.get("birthPos", "0_0").split("_")
            active = s.pop("activeInstance", None)
            if active:
                active["left"] = True
                self.encounters._archive(s, active)
                if active.get("subId"):
                    boss = s["bounties"][active["subId"]]
                    boss.update(innerCount=0, lastExitTime=now_ms(), lastExitDamage=integer(active.get("damage")))
            s["scene"].update(mapId=map_id, x=integer(birth[0]), y=integer(birth[-1]), monsters=[], dead=False)
            return f"Moved local scene to {scene.get('name', map_id)}", {"type": "mapTransfer", "sceneId": map_id, "arg": arg}
        if command == "moveSpeed":
            speed = float(arg or 1)
            if not math.isfinite(speed) or not 0.05 <= speed <= 100:
                raise SimulationError("INVALID_SPEED", "Use a local movement multiplier from 0.05 to 100")
            s["scene"]["moveSpeed"] = speed
            return f"Local movement multiplier is {speed:g}", {"type": "moveSpeed", "value": speed}
        if command == "setInsLv":
            parts = arg.split("_")
            if len(parts) != 2 or integer(parts[0], -1) < 1 or integer(parts[1], -1) < 1:
                raise SimulationError("INVALID_PARAMETERS", "Use instanceId_level")
            ref_id, level = integer(parts[0]), integer(parts[1])
            s["instanceLevels"][str(ref_id)] = level
            return f"Local instance {ref_id} set to level {level}", {"type": "instanceLevel", "refId": ref_id, "level": level}
        if command == "rebirthAll":
            s["scene"]["dead"] = False
            for monster in s["scene"]["monsters"]:
                monster["dead"] = False
                monster["hp"] = monster.get("maxHp", 100)
            return "Revived local scene actors", {"type": "rebirthAll"}
        if command == "addMonster":
            parts = (arg or str(next(iter(self.monsters), 100101))).split("_")
            ref_id, count = integer(parts[0]), integer(parts[1], 1) if len(parts) > 1 else 1
            if ref_id not in self.monsters or not 1 <= count <= 500:
                raise SimulationError("INVALID_MONSTER", "Select a captured monster ID and count from 1 to 500")
            created = []
            for index in range(count):
                row = {"uid": secrets.token_hex(8), "refId": ref_id, "hp": 100, "maxHp": 100, "dead": False,
                       "x": s["scene"]["x"] + 60 + index * 24, "y": s["scene"]["y"]}
                created.append(row)
            s["scene"]["monsters"].extend(created)
            return f"Spawned {count} local test monsters", {"type": "addMonster", "monsters": created}
        if command == "addMail":
            parts = arg.split("|", 2)
            title = parts[0] or "Offline test mail"
            content = parts[1] if len(parts) > 1 else "Created by the offline GM panel."
            attachment = parts[2] if len(parts) > 2 else "1_102_100"
            self._costs(attachment)
            sequence = max((m["emailId"] for m in s["mail"]), default=0) + 1
            s["mail"].append(self._mail(sequence, title, content, attachment))
            return f"Created local mail {sequence}", {"type": "refreshMail", "emailId": sequence}
        if command in ("sendSystemMsg", "sendRollNotice"):
            if not arg:
                raise SimulationError("EMPTY_MESSAGE", "Enter a local message")
            message = {"type": "system" if command == "sendSystemMsg" else "announcement", "text": arg[:2000], "at": now_ms()}
            s["messages"].append(message)
            s["messages"] = s["messages"][-200:]
            return "Added a local message; no message was sent to another player", {"type": "message", **message}
        if command in ("mainTask", "task"):
            ref_id = integer(arg, -1)
            if ref_id not in self.task_refs:
                raise SimulationError("UNKNOWN_TASK", "Select a captured TaskMainRef ID")
            self._complete_task(s, ref_id)
            s["settings"]["mainTask"] = ref_id
            return f"Local task {ref_id} is ready to claim", {"type": "refreshTasks"}
        if command == "tower":
            floor = integer(arg, -1)
            if not 1 <= floor <= 10000:
                raise SimulationError("INVALID_FLOOR", "Use a tower floor from 1 to 10000")
            s["towerFloor"] = floor
            return f"Local tower floor set to {floor}", {"type": "towerFloor", "floor": floor}
        if command == "limitAttr":
            ref_id = integer(arg, -1)
            row=next((r for r in self.table('LimitAttrRef') if integer(r['refId'])==ref_id),None)
            if row is None:
                raise SimulationError("INVALID_ATTRIBUTE", "Enter a positive captured attribute reference ID")
            s["limitAttrs"][str(ref_id)] = {"active": True, "activatedAt": now_ms(), "expiresAt": now_ms() + integer(row['effect'])*1000}
            return f"Activated captured temporary attributes {ref_id}", {"type": "refreshAttributes"}
        if command == "guildAuction":
            if not arg:
                raise SimulationError("INVALID_AUCTION", "Enter a local test transaction identifier")
            s["auctions"].append({"transactionId": arg[:200], "state": "simulated-completed", "at": now_ms()})
            return "Recorded a simulated guild auction; no multiplayer transaction occurred", {"type": "refreshGuild"}
        if command in ("prisonIn", "prisonOut"):
            s["scene"]["prison"] = command == "prisonIn"
            return "Local prison state updated", {"type": "prison", "inside": s["scene"]["prison"]}
        if command == "stageFb":
            stage = integer(arg, -1)
            if stage < 1:
                raise SimulationError("INVALID_STAGE", "Enter a positive stage reference ID")
            s["scene"]["stage"] = stage
            return f"Local stage instance marker set to {stage}", {"type": "stageFb", "refId": stage}
        if command == "openTipShow":
            s["settings"]["previewFunction"] = integer(arg)
            return "Requested a client feature-unlock preview", {"type": "openTipShow", "refId": integer(arg)}
        if command in ("actorSpine", "monsterSpine", "TrajectorySpine"):
            return "Requested original client asset preview", {"type": "assetPreview", "category": {"actorSpine": "character", "monsterSpine": "monster", "TrajectorySpine": "projectile"}[command]}
        if command == "hide":
            s["settings"]["hideUI"] = arg == "1"
            return "Local interface visibility changed", {"type": "hide", "hidden": arg == "1"}
        if command == "LayaGC":
            return "Requested release of unused client rendering resources", {"type": "LayaGC"}
        raise SimulationError("UNSUPPORTED_GM_COMMAND", f"Unknown local GM command {command!r}; no state was changed")

    def battle(self, account: str | dict, monster_ref_id: int, count=1) -> dict:
        """Deterministic local test battle. Rewards and damage are explicit approximations."""
        with self._lock:
            username = self._username(account)
            state = self._read(username)
            monster_ref_id, count = integer(monster_ref_id), max(1, min(100, integer(count, 1)))
            if monster_ref_id not in self.monsters:
                return self._error(0, "UNKNOWN_MONSTER", "Select a captured monster reference")
            fighters = [g for g in self._roster(state) if g["isSelect"]]
            if not fighters:
                return self._error(0, "NO_FIGHTERS", "Select at least one local character")
            power = sum(next(a["doubleValue"] for a in g["attrs"] if a["key"] == "power") for g in fighters)
            reward = [self._change_item(state, 102, 10 * count), self._change_item(state, 103, count)]
            state["scene"]["monsters"] = [m for m in state["scene"]["monsters"] if m["refId"] != monster_ref_id]
            self._write(username, state)
            return {"ok": True, "capability": "approximated", "offlineOnly": True, "victory": True,
                    "monsterRefId": monster_ref_id, "count": count, "partyPower": power, "rewards": reward,
                    "note": "Local deterministic test battle; production combat/reward algorithms are not available."}
