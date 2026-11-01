"""Recovered crew, Treasure, Talent and Gem progression for the offline game.

The request shapes, costs, per-character Treasure associations, cumulative rows and
1/10000 attribute units come from the original client. Achievement-slot `need`
values are treated as non-consuming thresholds, consistent with their captured
column/UI semantics. Production server code was not recovered.

Integration: create ``OfflineProgression(store)`` before OfflineStats. Call
``initialize_state`` for seeds/read migrations; call ``dispatch`` before the
legacy dispatcher and use its tuple when non-None. Forward ``_pendingBroadcasts``
through the existing command result. Append ``stat_sources`` to each character's
sources before summing raw attributes. No method performs persistence/network IO.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import math


def as_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError, OverflowError):
        return default


def attrs(encoded):
    result = defaultdict(float)
    for part in str(encoded or "").split("#"):
        fields = part.split("_")
        if len(fields) >= 2 and fields[0]:
            result[as_int(fields[0])] += float(fields[1] or 0)
    return dict(result)


def fail(code, message):
    # Lazy import keeps this module usable from OfflineStore.__init__ without a cycle.
    from offline_core import SimulationError
    raise SimulationError(code, message)


class OfflineProgression:
    handled_ids = frozenset({1300, 1304, 1305, 1307, 1400, 1402, 1405, 1500, 1501, 1502,
                             3320, 3321, 3322, 10100, 10101, 10102, 10103})
    achievement_type = 5

    def __init__(self, store):
        self.store = store
        self.fights = self._index("GeneralFightRef")
        self.treasures = self._index("TreasureRef")
        self.treasure_stars = {(as_int(row["refId"]), as_int(row["star"])): row for row in store.table("TreasureStarRef")}
        self.treasure_materials = self._index("TreasureMaterialRef")
        self.talents = self._index("TalentRef")
        self.advanced_talents = self._index("TalentAdvanceRef")
        self.gems = self._index("GemRef")
        self.gem_slots = self._index("GemSlotRef")
        self.gem_book = {as_int(row["order"]): row for row in store.table("GemBookStageRef")}
        self.achievements = self._index("TaskAchieveRef")

    def _index(self, name):
        return {as_int(row["refId"]): row for row in self.store.table(name)}

    def _owned(self, state, gid):
        general = state["generals"].get(str(gid))
        if general is None:
            fail("CHARACTER_NOT_OWNED", f"Character {gid} is not owned by this offline account")
        return general

    def initialize_state(self, state):
        """Migrate old saves without resetting inventory or deployed characters."""
        changed = False
        if "activeFights" not in state:
            points = as_int(state.get("inventory", {}).get("109"))
            selected_count = sum(bool(g.get("isSelect")) for g in state.get("generals", {}).values())
            unlocked = []
            for slot_id, row in sorted(self.fights.items()):
                needs = self.store._costs(row.get("need", ""))
                earned = not needs or all(as_int(state.get("inventory", {}).get(str(rid))) >= count for rid, count in needs)
                preserve_selection = as_int(row.get("type")) == 1 and as_int(row.get("num")) <= selected_count
                if earned or preserve_selection:
                    unlocked.append(slot_id)
            state["activeFights"] = unlocked
            state.setdefault("progressionMigrations", {})["crewSlots"] = {
                "version": 1, "achievementPoints": points,
                "basis": "captured thresholds plus already deployed crew preserved from legacy save",
            }
            changed = True
        free_ids = {ref_id for ref_id, row in self.fights.items() if not row.get("need")}
        normalized = sorted(free_ids | {as_int(value) for value in state["activeFights"] if as_int(value) in self.fights})
        if normalized != state["activeFights"]:
            state["activeFights"] = normalized
            changed = True
        defaults = {"treasures": {}, "talent": {"refIds": [], "advanceIds": []},
                    "gemBookStage": 0, "gemSlots": [], "achievementClaims": []}
        for key, value in defaults.items():
            if key not in state:
                state[key] = deepcopy(value)
                changed = True
        return changed

    def active_fights(self, state):
        self.initialize_state(state)
        return sorted({as_int(value) for value in state["activeFights"] if as_int(value) in self.fights})

    def crew_capacity(self, state):
        return sum(as_int(self.fights[ref_id].get("type")) == 1 for ref_id in self.active_fights(state))

    def _emit(self, state, command_id, data):
        state.setdefault("_pendingBroadcasts", []).append({"id": command_id, "data": deepcopy(data)})

    def _roster(self, state):
        return self.store._roster(state)

    def _refresh_roster(self, state):
        self._emit(state, 1302, {"generals": self._roster(state)})

    def general_list(self, state):
        return {"generals": self._roster(state), "activeFights": self.active_fights(state),
                "freeResetCount": 99, "skins": list(state.get("generalSkins", {}).values()),
                "echoRefId": self.store.systems.echo(state), "foorprints": list(state.get("footprints",{}).values()), "skillSkins": list(state.get("skillSkins",{}).values()) if isinstance(state.get("skillSkins",{}),dict) else state.get("skillSkins",[]),
                "petId": state.get("settings", {}).get("petAppearId", 0)}

    def _task_progress(self, state, row):
        fields = str(row.get("finishCondition", "")).split("_")
        kind = as_int(fields[0])
        progression = state.get("progression", {})
        if kind == 1:
            return as_int(state.get("player", {}).get("level")), True
        if kind == 7:
            return as_int(state.get("player", {}).get("loginDays"), 1), True
        if kind == 11:
            return sum(as_int(count) for count in progression.get("kills", {}).values()), True
        if kind == 15:
            # Original main-task sync identifies type-2 NPCs as opened fog regions.
            return sum(as_int(self.store.npcs.get(nid, {}).get("type")) == 2 for nid in state.get("unlockedNpcIds", [])), True
        if kind == 17:
            return as_int(progression.get("diamondsSpent")), True
        if kind == 18:
            return len(state.get("generals", {})), True
        if kind == 23:
            target = as_int(fields[2]) if len(fields) > 2 else 0
            return int(target in progression.get("mapsVisited", [])), True
        if kind == 37:
            return as_int(next((value["attrValue"] for value in state.get("player", {}).get("attrs", []) if as_int(value.get("attrType")) == 1000), 0)), True
        if kind == 40:
            return max(0, as_int(state.get("towerFloor"), 1) - 1), True
        if kind == 41:
            unlocked = state.get("talent", {}).get("refIds", [])
            return max((as_int(self.talents.get(as_int(ref_id), {}).get("level")) for ref_id in unlocked), default=0), True
        if kind == 46:
            return sum(as_int(count) for count in progression.get("gathered", {}).values()), True
        # Unrecovered activity counters stay unachieved rather than fabricating progress.
        return 0, False

    def sync_achievements(self, state):
        self.initialize_state(state)
        tasks = state.setdefault("tasks", [])
        existing = {as_int(task["refId"]): task for task in tasks if as_int(task.get("type")) == self.achievement_type}
        claims = {as_int(value) for value in state["achievementClaims"]}
        claims.update(ref_id for ref_id, task in existing.items() if as_int(task.get("state")) == 3)
        changed = False
        for ref_id, row in sorted(self.achievements.items()):
            predecessor = as_int(row.get("preTask"))
            if predecessor and predecessor not in claims:
                continue
            if as_int(state.get("player", {}).get("level"), 1) < as_int(row.get("lv"), 1):
                continue
            task = existing.get(ref_id)
            if task is None:
                task = {"type": self.achievement_type, "refId": ref_id, "state": 1, "progress": 0, "extInfo": ""}
                tasks.append(task)
                existing[ref_id] = task
                changed = True
            if ref_id in claims:
                if task["state"] != 3:
                    task["state"] = 3
                    changed = True
                continue
            progress, supported = self._task_progress(state, row)
            if not supported:
                task["extInfo"] = "Offline counter not reconstructed"
                continue
            limit = max(1, as_int(row.get("count"), 1))
            progress = min(limit, max(as_int(task.get("progress")), progress))
            status = 2 if progress >= limit else 1
            if progress != task["progress"] or status != task["state"]:
                task.update(progress=progress, state=status)
                changed = True
        state["achievementClaims"] = sorted(claims)
        return changed

    def _claim_achievement(self, state, ref_id):
        self.sync_achievements(state)
        task = next((task for task in state["tasks"] if task["type"] == self.achievement_type and task["refId"] == ref_id), None)
        row = self.achievements.get(ref_id)
        if not row or not task:
            fail("UNKNOWN_ACHIEVEMENT", "Select an available captured achievement")
        if task["state"] == 3:
            fail("ALREADY_CLAIMED", "This achievement reward has already been claimed")
        if task["state"] != 2:
            fail("REWARD_NOT_READY", "The captured achievement condition is not complete")
        rewards = self.store._grant(state, row.get("reward", ""))
        task["state"] = 3
        if ref_id not in state["achievementClaims"]:
            state["achievementClaims"].append(ref_id)
        self.sync_achievements(state)
        return rewards

    def dispatch(self, state, cid, payload=None):
        """Return a core-compatible tuple, or None for legacy/non-scope requests."""
        cid, p = as_int(cid), payload or {}
        if cid not in self.handled_ids:
            return None
        if cid in (1402, 1405) and as_int(p.get("type")) != self.achievement_type:
            return None
        migrated = self.initialize_state(state)
        if cid == 1300:
            return self.general_list(state), migrated, "reference-driven"
        if cid == 1307:
            ref_id = as_int(p.get("refId"))
            row = self.fights.get(ref_id)
            if not row:
                fail("UNKNOWN_CREW_SLOT", "Use a GeneralFightRef slot/achievement reference ID")
            unlocked = self.active_fights(state)
            if ref_id in unlocked:
                return {"activeFights": unlocked}, migrated, "reference-driven"
            previous = [key for key, value in self.fights.items() if as_int(value.get("nextRefId")) == ref_id]
            if previous and not any(key in unlocked for key in previous):
                fail("PREVIOUS_SLOT_REQUIRED", "Unlock the preceding crew/achievement stage first")
            for item_id, count in self.store._costs(row.get("need", "")):
                if as_int(state["inventory"].get(str(item_id))) < count:
                    fail("ACHIEVEMENT_POINTS_REQUIRED", f"This crew stage requires {count} achievement points; these are not consumed")
            state["activeFights"] = sorted(unlocked + [ref_id])
            self._refresh_roster(state)
            return {"activeFights": state["activeFights"]}, True, "reference-driven-threshold"
        if cid in (1304, 1305):
            gid = as_int(p.get("generalId"))
            general = self._owned(state, gid)
            changed = False
            if cid == 1305:
                changed = bool(general.get("isSelect"))
                general["isSelect"] = False
                # Undeployment preserves ownership, levels, gear and unlocked slots.
                reply = {"general": {**general, "attrs": self.store._attrs(state, general)}, "reward": [], "equips": state["equipment"], "echoRefId": self.store.systems.echo(state)}
            else:
                replace_id = as_int(p.get("replaceGeneralId"))
                if not general.get("isSelect"):
                    selected = [g for g in state["generals"].values() if g.get("isSelect")]
                    if replace_id:
                        replacement = self._owned(state, replace_id)
                        if replace_id == gid or not replacement.get("isSelect"):
                            fail("INVALID_REPLACEMENT", "Choose a different currently deployed character to replace")
                        replacement["isSelect"] = False
                    elif len(selected) >= self.crew_capacity(state):
                        fail("CREW_FULL", "Unlock another crew slot with achievement points, or choose a deployed character to replace")
                    general["isSelect"] = True
                    changed = True
                reply = {"generals": self._roster(state), "reward": [], "equips": state["equipment"], "echoRefId": self.store.systems.echo(state)}
            if changed:
                self._refresh_roster(state)
            return reply, migrated or changed, "reference-driven"
        if cid == 1400:
            changed = self.sync_achievements(state)
            return {"taskInfos": self.store._visible_tasks(state), "activeRewardInfos": [], "finishMapBigIds": state.get("finishMapBigIds",[])}, migrated or changed, "reference-driven"
        if cid in (1402, 1405):
            self.sync_achievements(state)
            if cid == 1402:
                rewards = self._claim_achievement(state, as_int(p.get("refId")))
            else:
                rewards = []
                # Newly exposed chain members are claimable only if their own condition is met.
                for _ in range(len(self.achievements) + 1):
                    ready = [task["refId"] for task in state["tasks"] if task["type"] == self.achievement_type and task["state"] == 2]
                    if not ready:
                        break
                    for ref_id in ready:
                        rewards.extend(self._claim_achievement(state, ref_id))
            visible = [task for task in state["tasks"] if task["type"] == self.achievement_type]
            self._emit(state, 1401, {"taskInfos": visible})
            return {"reward": rewards, "taskInfos": visible}, bool(rewards) or migrated, "reference-driven"
        if cid == 1500:
            return {"info": deepcopy(state["talent"])}, migrated, "reference-driven"
        if cid in (1501, 1502):
            advanced = cid == 1502
            key, refs = ("advanceIds", self.advanced_talents) if advanced else ("refIds", self.talents)
            owned = {as_int(value) for value in state["talent"][key]}
            next_id = max(owned, default=0) + 1
            row = refs.get(next_id)
            if row is None:
                fail("MAX_TALENT", "All captured talent nodes in this track are active")
            required_level = as_int(row.get("level"), 1)
            if as_int(state["player"].get("level"), 1) < required_level:
                fail("PLAYER_LEVEL_REQUIRED", f"This talent requires player level {required_level}")
            if advanced:
                basic_level = max((as_int(self.talents.get(as_int(value), {}).get("level")) for value in state["talent"]["refIds"]), default=0)
                if basic_level < required_level:
                    fail("BASIC_TALENT_REQUIRED", f"Activate basic talents through level {required_level} first")
            self.store._spend(state, row.get("cost", ""))
            state["talent"][key] = sorted(owned | {next_id})
            self._refresh_roster(state)
            return {"info": deepcopy(state["talent"])}, True, "reference-driven"
        if cid == 3320:
            return {"infos": list(deepcopy(state["treasures"]).values())}, migrated, "reference-driven"
        if cid == 3321:
            ref_id = as_int(p.get("refId"))
            if ref_id not in self.treasures:
                fail("UNKNOWN_TREASURE", "Select a captured TreasureRef identifier")
            current = state["treasures"].get(str(ref_id), {"refId": ref_id, "star": 0, "materials": []})
            next_star = as_int(current.get("star")) + 1
            row = self.treasure_stars.get((ref_id, next_star))
            if row is None:
                fail("MAX_TREASURE_STAR", "This Treasure is at the captured maximum star")
            self.store._spend(state, row.get("cost", ""))
            current["star"] = next_star
            state["treasures"][str(ref_id)] = current
            self._refresh_roster(state)
            return {"info": deepcopy(current)}, True, "reference-driven"
        if cid == 3322:
            ref_id = as_int(p.get("refId"))
            current = state["treasures"].get(str(ref_id))
            if current is None:
                fail("TREASURE_NOT_OWNED", "Activate this Treasure before adding materials")
            addition = p.get("addNum")
            if not isinstance(addition, dict):
                fail("INVALID_PARAMETERS", "Use addNum: {refId: materialId, count: quantity}")
            material_id, count = as_int(addition.get("refId")), as_int(addition.get("count"), -1)
            row = self.treasure_stars.get((ref_id, as_int(current["star"])))
            limits = self._limits((row or {}).get("materialLimit", ""))
            if material_id not in self.treasure_materials or material_id not in limits or count <= 0:
                fail("INVALID_TREASURE_MATERIAL", "Select an allowed material and a positive count")
            existing = next((value for value in current["materials"] if as_int(value["refId"]) == material_id), None)
            old_count = as_int((existing or {}).get("count"))
            if old_count + count > limits[material_id]:
                fail("MATERIAL_LIMIT", f"This Treasure star permits at most {limits[material_id]} of material {material_id}")
            self.store._spend(state, f"1_{material_id}_{count}")
            if existing is None:
                existing = {"refId": material_id, "count": 0}
                current["materials"].append(existing)
            existing["count"] += count
            self._refresh_roster(state)
            return {"info": deepcopy(current)}, True, "reference-driven"
        if cid == 10100:
            return {"bookStage": as_int(state["gemBookStage"]), "slotInfos": deepcopy(state["gemSlots"])}, migrated, "reference-driven"
        if cid == 10103:
            next_stage = as_int(state["gemBookStage"]) + 1
            row = self.gem_book.get(next_stage)
            if row is None:
                fail("MAX_GEM_MASTER", "Gem Master is at the captured maximum stage")
            self.store._spend(state, row.get("cost", ""))
            state["gemBookStage"] = next_stage
            self._refresh_roster(state)
            return {"bookStage": next_stage}, True, "reference-driven"
        if cid in (10101, 10102):
            return self._gem_equipment(state, cid, p, migrated)
        return None

    @staticmethod
    def _limits(value):
        return {as_int(part.split("_")[0]): as_int(part.split("_")[1]) for part in value.split("#") if len(part.split("_")) == 2}

    def _gem_equipment(self, state, cid, payload, migrated):
        slots = payload.get("slotInfos")
        if not isinstance(slots, list) or len(slots) > 1000:
            fail("INVALID_GEM_SLOTS", "slotInfos must be a bounded list of gem-slot entries")
        previous = {(as_int(value["generalId"]), as_int(value["slotRefId"])): deepcopy(value) for value in state["gemSlots"]}
        seen, operations = set(), []
        delta = defaultdict(int)
        for value in slots:
            if not isinstance(value, dict):
                fail("INVALID_GEM_SLOTS", "Each gem slot must be an object")
            gid, slot_id, item_id = as_int(value.get("generalId")), as_int(value.get("slotRefId")), as_int(value.get("itemId"))
            key = (gid, slot_id)
            if key in seen:
                fail("DUPLICATE_GEM_SLOT", "A gem slot may occur only once in a request")
            seen.add(key)
            general = self._owned(state, gid)
            slot = self.gem_slots.get(slot_id)
            if slot is None:
                fail("UNKNOWN_GEM_SLOT", "Select a captured GemSlotRef identifier")
            old = previous.get(key)
            if cid == 10102:
                if old is None:
                    continue  # Idempotent undress: no gem and no refund.
                if item_id and item_id != as_int(old["itemId"]):
                    fail("GEM_MISMATCH", "The requested item does not match the gem in this slot")
                delta[as_int(old["itemId"])] += 1
                operations.append((key, None, old))
                continue
            gem = self.gems.get(item_id)
            if gem is None:
                fail("UNKNOWN_GEM", "Select an owned captured GemRef item")
            allowed_types = {as_int(value) for value in slot.get("types", "").split("#") if value}
            if as_int(gem.get("type")) not in allowed_types:
                fail("GEM_TYPE_MISMATCH", "This gem's type does not fit the selected slot")
            if as_int(general.get("star")) < as_int(slot.get("star")):
                fail("STAR_REQUIRED", f"This gem slot requires character star {slot.get('star')}")
            if old and as_int(old["itemId"]) == item_id:
                continue  # Idempotent dress: do not consume another copy.
            if old:
                delta[as_int(old["itemId"])] += 1
            delta[item_id] -= 1
            operations.append((key, {"generalId": gid, "slotRefId": slot_id, "itemId": item_id}, old))
        for item_id, difference in delta.items():
            if as_int(state["inventory"].get(str(item_id))) + difference < 0:
                fail("INSUFFICIENT_ITEMS", f"Not enough copies of gem {item_id} for the whole request")
        for item_id, difference in delta.items():
            if difference:
                self.store._change_item(state, item_id, difference)
        changed_slots, rewards = [], []
        for key, new, old in operations:
            if new is None:
                previous.pop(key, None)
                changed_slots.append(old)
                rewards.append({"refId": old["itemId"], "count": 1, "attrs": []})
            else:
                previous[key] = new
                changed_slots.append(new)
        state["gemSlots"] = list(previous.values())
        if operations:
            self._refresh_roster(state)
        return {"slotInfos": changed_slots, "reward": rewards}, bool(operations) or migrated, "reference-driven"

    def stat_sources(self, state, general):
        """Flat/captured-percent contributions, before the existing stat engine stacks them."""
        result = []
        gid = as_int(general["generalId"])
        for ref_id in state.get("activeFights", []):
            row = self.fights.get(as_int(ref_id), {})
            if row.get("attrs"):
                result.append({"source": f"Achievement crew stage {ref_id}", "attrs": attrs(row["attrs"])})
        for key, refs, title in (("refIds", self.talents, "Talent"), ("advanceIds", self.advanced_talents, "Advanced Talent")):
            for ref_id in state.get("talent", {}).get(key, []):
                row = refs.get(as_int(ref_id), {})
                if row.get("attrs"):
                    result.append({"source": f"{title} {ref_id}", "attrs": attrs(row["attrs"])})
        for owned in state.get("treasures", {}).values():
            treasure_id = as_int(owned["refId"])
            ref = self.treasures.get(treasure_id, {})
            associated = {as_int(value) for value in ref.get("generals", "").split("#") if value}
            if gid not in associated:
                continue
            row = self.treasure_stars.get((treasure_id, as_int(owned["star"])))
            if row is None:
                continue
            result.append({"source": f"Treasure {treasure_id}, star {owned['star']} (current cumulative row)", "attrs": attrs(row.get("attrs", ""))})
            limits = self._limits(row.get("materialLimit", ""))
            for material in owned.get("materials", []):
                material_id = as_int(material["refId"])
                count = min(max(0, as_int(material.get("count"))), limits.get(material_id, 0))
                definition = self.treasure_materials.get(material_id, {})
                if count and definition:
                    result.append({"source": f"Treasure {treasure_id}, material {material_id} × {count}",
                                   "attrs": {attr: value * count for attr, value in attrs(definition.get("attrs", "")).items()}})
        stage = as_int(state.get("gemBookStage"))
        book = self.gem_book.get(stage)
        if book:
            result.append({"source": f"Gem Master {stage} (current cumulative row)", "attrs": attrs(book.get("attrs", ""))})
        for slot in state.get("gemSlots", []):
            if as_int(slot.get("generalId")) == gid:
                row = self.gems.get(as_int(slot.get("itemId")), {})
                if row:
                    result.append({"source": f"Gem {slot['itemId']} in slot {slot['slotRefId']}", "attrs": attrs(row.get("attrs", ""))})
        return [value for value in result if any(value["attrs"].values())]
