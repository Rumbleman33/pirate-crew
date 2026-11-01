"""Reference-driven, account-local encounters for the original browser client.

Captured costs, monsters, waves, rank rewards and protocol fields are reused.
Production server arbitration is not available: damage accepts the recovered
client's calculated hit values; reward-group rolls use a reproducible local seed.
There is no network or cross-account state in this module.
"""
from __future__ import annotations

from copy import deepcopy
from collections import defaultdict
import hashlib
import math
from pathlib import Path
import random
import re
import time


def integer(value, default=0):
    try:
        return int(float(value))
    except (ValueError, TypeError, OverflowError):
        return default


def finite(value, default=0.0):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (ValueError, TypeError, OverflowError):
        return default


def fail(code, message):
    # Lazy import permits OfflineStore to import this component at module load.
    from offline_core import SimulationError
    raise SimulationError(code, message)


class OfflineEncounters:
    handled_ids = frozenset({50010, 50101, 51001, 51002, 51004, 51005, 51007,
                             51050, 51051, 52001, 52002, 52003, 52005, 52007, 52009})

    def __init__(self, store, clock=None):
        self.store = store
        self.clock = clock or (lambda: int(time.time() * 1000))
        self.subs = {r["subId"]: r for r in store.table("WorldBossSubRef")}
        self.bounty_instances = defaultdict(list)
        self.bounty_rewards = defaultdict(list)
        self.reward_groups = defaultdict(list)
        self.item_groups = defaultdict(list)
        for row in store.table("WorldBossInsRef"):
            self.bounty_instances[integer(row["groupId"])].append(row)
        for row in store.table("WorldBossRewardRef"):
            self.bounty_rewards[integer(row["groupId"])].append(row)
        for row in store.table("RewardGroupRef"):
            self.reward_groups[integer(row["rewardGroupId"])].append(row)
        for row in store.table("RewardItemGroupRef"):
            self.item_groups[integer(row["groupId"])].append(row)
        self.attr_names = {r["attr"]: integer(r["refId"]) for r in store.table("AttrRef")}

    def now(self):
        return integer(self.clock())

    def dispatch(self, state, cid, payload):
        """Apply atomically; failed validation never partly spends or grants."""
        cid = integer(cid)
        if cid not in self.handled_ids:
            fail("UNSUPPORTED_ENCOUNTER", f"Encounter component does not handle command {cid}")
        candidate = deepcopy(state)
        reply, mutated, capability = self._dispatch(candidate, cid, payload or {})
        if mutated:
            state.clear()
            state.update(candidate)
        return reply, mutated, capability

    @staticmethod
    def _push(state, cid, data):
        state.setdefault("_pendingBroadcasts", []).append({"id": cid, "data": deepcopy(data)})

    def _sub(self, sub_id):
        sub_id = str(sub_id or "")
        if sub_id not in self.subs:
            fail("UNKNOWN_BOUNTY", "Bounty is absent from the captured reference tables")
        return self.subs[sub_id]

    def _bounty_ref(self, state, sub):
        days = integer(state.get("settings", {}).get("serverAgeDays"), 365)
        candidates = [r for r in self.bounty_instances[integer(sub["insGroup"])]
                      if (integer(r["startDay"]) < 0 or integer(r["startDay"]) <= days)
                      and (integer(r["endDay"]) < 0 or integer(r["endDay"]) >= days)]
        if not candidates:
            fail("NO_BOUNTY_INSTANCE", "No captured bounty instance matches the simulated server age")
        return max(candidates, key=lambda r: integer(r["startDay"]))

    def _boss(self, state, sub_id):
        boss = state.setdefault("bounties", {}).setdefault(sub_id, {})
        for key, value in {"hpRate": 10000, "innerCount": 0, "nextRefreshTime": 0,
                           "enterIds": [], "cycle": 1, "scores": {}, "records": [],
                           "lastExitTime": 0, "lastExitDamage": 0}.items():
            boss.setdefault(key, deepcopy(value))
        refreshed = False
        if boss["nextRefreshTime"] and integer(boss["nextRefreshTime"]) <= self.now():
            boss.update(hpRate=10000, innerCount=0, nextRefreshTime=0, enterIds=[],
                        cycle=integer(boss["cycle"], 1) + 1, scores={}, lastExitTime=0)
            refreshed = True
        return boss, refreshed

    def _boss_info(self, state, sub_id):
        sub = self._sub(sub_id)
        boss, refreshed = self._boss(state, sub_id)
        bypass = bool(state.get("settings", {}).get("allFunctionsOpen"))
        unlocked = bypass or not sub.get("condition")
        return {"subActivityId": sub_id, "hpRate": max(0, min(10000, integer(boss["hpRate"]))),
                "nextRefreshTime": integer(boss["nextRefreshTime"]),
                "innerCount": max(0, integer(boss["innerCount"])),
                "enterIds": list(boss["enterIds"]), "unlocked": unlocked}, refreshed

    def _rank(self, state, sub_id):
        boss, _ = self._boss(state, sub_id)
        scores = boss["scores"]
        pid = str(state["playerId"])
        score = max(0, integer(scores.get(pid)))
        player = state["player"]
        ranks = []
        if score > 0:
            ranks.append({"playerId": state["playerId"], "playerName": player["nickname"],
                          "personality": deepcopy(player["personality"]), "extInfo": "offline-local",
                          "playerScore": score, "level": player["level"], "vipLevel": player["vipLevel"],
                          "serverId": 1, "reportTime": self.now(), "power": self._crew_power(state)})
        return {"subActivityId": sub_id, "rankInfos": ranks,
                "myRank": {"myRank": 1 if score > 0 else -1, "myScore": score,
                           "extInfo": "offline-local", "initScore": 0, "maxScore": score}}

    def _crew_power(self, state):
        return integer(sum(finite(a.get("doubleValue")) for g in self.store._roster(state)
                           if g.get("isSelect") for a in self.store._attrs(state, g) if a.get("key") == "power"))

    def _dispatch(self, state, cid, payload):
        if cid in (52001, 52009):
            wanted = integer(payload.get("type")) if cid == 52009 else 0
            infos, changed = [], False
            for sub_id, sub in self.subs.items():
                if wanted and integer(sub["type"]) != wanted:
                    continue
                info, refreshed = self._boss_info(state, sub_id)
                infos.append(info)
                if refreshed:
                    self._push(state, 52008, {"info": [info]})
                    changed = True
            return {"infos": infos, **({"serverId": []} if cid == 52001 else {})}, changed, "simulated"
        if cid == 52002:
            return self._enter_bounty(state, payload), True, "approximated"
        if cid == 52003:
            return self._leave_bounty(state, payload), True, "simulated"
        if cid == 52005:
            sub_id = str(payload.get("subActivityId", ""))
            self._sub(sub_id)
            _, refreshed = self._boss(state, sub_id)
            return self._rank(state, sub_id), refreshed, "simulated"
        if cid == 52007:
            sub_id = str(payload.get("subActivityId", ""))
            self._sub(sub_id)
            boss, refreshed = self._boss(state, sub_id)
            return {"subActivityId": sub_id, "records": deepcopy(boss["records"][:50])}, refreshed, "simulated"
        if cid == 51001:
            return {"infos": [{"refId": integer(k), "lv": integer(v)} for k, v in state.get("instanceLevels", {}).items()]}, False, "simulated"
        if cid == 51002:
            return {"data": self._enter_instance(state, payload)}, True, "approximated"
        if cid == 51005:
            active = self._active(state, payload.get("uid"))
            if active.get("settled") or active.get("started"):
                return {}, False, "simulated"
            active["started"] = True
            active["data"]["startTime"] = self.now()
            self._push(state, 51006, {"uid": active["data"]["uid"], "startTime": self.now(), "playerId": state["playerId"]})
            return {}, True, "simulated"
        if cid == 51004:
            active = self._active(state, payload.get("uid"), history=True)
            changed = False
            if not active.get("settled"):
                victory = self._all_waves_dead(active)
                if victory:
                    self._finish(state, active)
                    changed = True
                elif payload.get("active") or self._expired(active):
                    self._finish(state, active, success=False)
                    changed = True
            return {"data": deepcopy(active["data"]), "success": bool(active.get("success")),
                    "infos": self._instance_info(state, active)}, changed, "approximated"
        if cid == 50010:
            return {}, self._damage(state, payload), "approximated"
        if cid == 50101:
            return {}, self._revive(state, payload), "simulated"
        if cid == 51050:
            ref_id, level = integer(payload.get("refId")), integer(payload.get("lv"), 1)
            self._instance_ref(ref_id, level)
            state.setdefault("instanceLevels", {})[str(ref_id)] = level
            return {"infos": {"refId": ref_id, "lv": level}}, True, "simulated"
        if cid in (51007, 51051):
            return self._sweep(state, cid, payload), True, "approximated"
        fail("UNSUPPORTED_ENCOUNTER", f"Unimplemented encounter command {cid}")

    def _instance_ref(self, ref_id, level):
        if ref_id not in self.store.instances:
            fail("UNKNOWN_INSTANCE", "Instance is absent from the captured reference tables")
        row = self.store.instance_refs.get((ref_id, level))
        if not row:
            fail("NO_INSTANCE_LEVEL", "No captured configuration for this instance level")
        return row

    def _active(self, state, uid=None, history=False):
        active = state.get("activeInstance")
        if active and (uid is None or integer(uid) == integer(active["data"]["uid"])):
            return active
        if history:
            for previous in reversed(state.get("encounterHistory", [])):
                if integer(uid) == integer(previous["data"]["uid"]):
                    return previous
        fail("NO_ACTIVE_INSTANCE", "This offline instance is no longer active")

    def _archive(self, state, active):
        history = state.setdefault("encounterHistory", [])
        uid = active["data"]["uid"]
        history[:] = [old for old in history if old["data"]["uid"] != uid]
        history.append(deepcopy(active))
        del history[:-12]

    def _ensure_available(self, state, kind, ref_id, level, sub_id=None, cycle=None):
        old = state.get("activeInstance")
        if not old:
            return None
        if old.get("settled") or old.get("left"):
            self._archive(state, old)
            return None
        if old.get("kind") == kind and old["data"]["refId"] == ref_id and old["data"]["lv"] == level and old.get("subId") == sub_id and old.get("cycle") == cycle:
            return old
        fail("ACTIVE_ENCOUNTER", "Leave the current local encounter before entering another")

    def _enter_bounty(self, state, payload):
        sub_id = str(payload.get("subActivityId", ""))
        sub = self._sub(sub_id)
        ref = self._bounty_ref(state, sub)
        boss, _ = self._boss(state, sub_id)
        if integer(boss["hpRate"]) <= 0 or integer(boss["nextRefreshTime"]) > self.now():
            fail("BOUNTY_REFRESHING", "This bounty is defeated and is waiting for its captured refresh timer")
        if not state.get("settings", {}).get("fullGM"):
            if state["player"]["level"] < integer(sub["lv"]) or state["player"]["vipLevel"] < integer(sub["vip"]):
                fail("BOUNTY_LOCKED", "Player level or VIP level does not meet the captured bounty requirement")
            if not self._boss_info(state, sub_id)[0]["unlocked"]:
                fail("BOUNTY_LOCKED", "The captured bounty unlock condition is not satisfied")
        ref_id = integer(ref["insId"])
        previous = self._ensure_available(state, "bounty", ref_id, 1, sub_id, boss["cycle"])
        if previous:
            return {"data": deepcopy(previous["data"]), "desc": self.store._scene_player(state)}
        remaining = integer(boss["lastExitTime"]) + integer(sub.get("enterCD")) * 1000 - self.now()
        if remaining > 0:
            fail("BOUNTY_REENTER_COOLDOWN", f"Wait {math.ceil(remaining / 1000)} seconds before re-entering this bounty")
        if integer(sub.get("maxJoinCount")) > 0 and integer(boss["innerCount"]) >= integer(sub["maxJoinCount"]):
            fail("BOUNTY_FULL", "The captured bounty participant limit has been reached")
        times = max(1, integer(payload.get("times"), 1))
        if times != 1:
            fail("UNSUPPORTED_BOUNTY_MULTIPLIER", "This local encounter currently supports one challenge at a time")
        active = self._make(state, ref_id, 1, payload.get("generals") or [], kind="bounty")
        active.update(subId=sub_id, bountyRef=deepcopy(ref), cycle=boss["cycle"], times=1)
        first_entry = state["playerId"] not in boss["enterIds"]
        if first_entry or integer(sub["type"]) in (3, 6):
            self.store._spend(state, sub.get("cost", ""))
        if first_entry:
            boss["enterIds"].append(state["playerId"])
            if ref.get("enterReward"):
                self._grant(state, ref["enterReward"], active, "entry")
        boss["innerCount"] = 1
        active["damage"] = 0
        # A partially damaged local bounty keeps its HP on leave/re-entry.
        for sprite in active["data"]["sprites"]:
            if sprite["type"] == 2 and sprite["id"] == integer(ref["bossMonster"]):
                hp = sprite["labile"]["hp"]
                hp["cur"] = max(1, hp["max"] * integer(boss["hpRate"]) // 10000)
        self._push(state, 52008, {"info": [self._boss_info(state, sub_id)[0]]})
        self._push(state, 52006, {**self._rank(state, sub_id), "playerId": state["playerId"]})
        return {"data": deepcopy(active["data"]), "desc": self.store._scene_player(state)}

    def _leave_bounty(self, state, payload):
        sub_id = str(payload.get("subActivityId", ""))
        sub = self._sub(sub_id)
        boss, _ = self._boss(state, sub_id)
        active = state.get("activeInstance")
        damage = integer(boss["lastExitDamage"])
        if active:
            if active.get("subId") != sub_id:
                fail("ENCOUNTER_MISMATCH", "The leave request does not match the active local bounty")
            damage = integer(active.get("damage"))
            boss.update(innerCount=0, lastExitTime=self.now(), lastExitDamage=damage)
            active["left"] = True
            self._archive(state, active)
            state.pop("activeInstance", None)
        info = self._boss_info(state, sub_id)[0]
        self._push(state, 52008, {"info": [info]})
        return {"info": info, "totalDamage": integer(boss["scores"].get(str(state["playerId"]))),
                "curDamage": damage, "times": 1, "subActivityId": sub_id, "type": integer(sub["type"]),
                "rebirthTime": max(0, integer(boss["nextRefreshTime"]) - self.now())}

    def _enter_instance(self, state, payload):
        active=state.get('activeInstance')
        if active and active.get('practice') and integer(payload.get('refId'))==201:return deepcopy(active['data'])
        ref_id, level = integer(payload.get("refId")), max(1, integer(payload.get("lv"), 1))
        self._instance_ref(ref_id, level)
        old = self._ensure_available(state, "stage-practice" if integer(self.store.instances[ref_id].get("type"))==27 else "instance", ref_id, level)
        if old:
            return deepcopy(old["data"])
        selected=payload.get('generals') or (state.get('tower',{}).get('generals',[]) if ref_id==201 else [])
        if integer(self.store.instances[ref_id].get('type'))==27:
            active=self.store.stages.enter(state,ref_id,level,selected)
        else:active = self._make(state, ref_id, level, selected, kind="instance")
        self.store._spend(state, self.store.instances[ref_id].get("cost", ""))
        return deepcopy(active["data"])

    def _make(self, state, ref_id, level, generals, kind, custom_waves=None):
        row = self._instance_ref(ref_id, level)
        scene = self.store.scenes.get(integer(row["sceneId"]), {})
        birth = (scene.get("birthPos") or "1792_1600").replace("#", "_").split("_")
        x, y = integer(birth[0]), integer(birth[1] if len(birth) > 1 else 1600)
        uid = max(self.now() * 100, integer(state.get("lastEncounterUid")) + 100000)
        state["lastEncounterUid"] = uid
        actors, seen = [], set()
        chosen = generals or [g["generalId"] for g in self.store._roster(state) if g.get("isSelect")]
        for number, selected in enumerate(chosen[:10]):
            gid = integer(selected.get("id", selected.get("generalId"))) if isinstance(selected, dict) else integer(selected)
            if gid in seen:
                continue
            seen.add(gid)
            self.store._general(state, gid)
            general = next(g for g in self.store._roster(state) if g['generalId']==gid)
            attrs = self.store._attrs(state, general)
            numbers = {a["key"]: finite(a.get("doubleValue", a.get("int64Value"))) for a in attrs}
            actor_uid = integer(selected.get("uid")) if isinstance(selected, dict) else 0
            actor_uid = actor_uid or uid + number + 1
            position = {"x": x + number * 70, "y": y, "dir": 0}
            hp = max(1, integer(numbers.get("hp"), 100))
            actor_attrs = [{"key": self.attr_names[key], "value": value} for key, value in numbers.items() if key in self.attr_names]
            actors.append({"uid": actor_uid, "id": gid, "type": 1, "labile": {"uid": actor_uid, "pos": position, "hp": {"max": hp, "cur": hp, "shield": 0}},
                           "attrs": actor_attrs, "skillList": list(general.get("skillIds", [])), "entryIds": [e for g in self.store._roster(state) if g['generalId']==gid for e in g.get('entryInfos',[])], "playerId": state["playerId"],
                           "campId": state["playerId"], "skinId": general.get("skinId", 0), "footprintId": general.get("footprintId", 0), "brithPos": position})
        if not actors:
            fail("NO_DEPLOYED_CREW", "Deploy at least one owned character before entering an encounter")
        waves = []
        for index, wave in enumerate(sorted(custom_waves if custom_waves is not None else self.store.instance_waves.get(integer(row["refreshConfig"]), []), key=lambda r: integer(r["wave"]))):
            sprites = []
            for entry in (wave.get("data") or "").split("#"):
                bits = entry.split("_")
                if len(bits) < 4:
                    continue
                monster_id, count, mx, my = (integer(value) for value in bits[:4])
                radius=max(1,integer(bits[4],50)) if len(bits)>4 else 50
                # Zero coordinates are a relative spawn marker, not the origin
                # of the map. Retain real authored tower/boss positions.
                if mx==0 and my==0:mx,my=x+150,y
                monster = self.store.monsters.get(monster_id)
                if not monster:
                    fail("UNKNOWN_MONSTER", f"Encounter wave references missing monster {monster_id}")
                if not 1 <= count <= 100:
                    fail("UNSUPPORTED_WAVE_SIZE", "Captured monster count is outside the local encounter safety limit")
                attrs = []
                for encoded in (monster.get("attrs") or "").split("#"):
                    fields = encoded.split("_")
                    if len(fields) >= 2:
                        attrs.append({"key": integer(fields[0]), "value": finite(fields[1])})
                hp = max(1, integer(next((a["value"] for a in attrs if a["key"] == 2), 100)))
                for n in range(count):
                    monster_uid = uid + 1000 + index * 1000 + len(sprites)
                    angle=n*2.3999632297
                    spread=min(radius,10*(n+1))
                    point = {"x": mx+round(math.cos(angle)*spread), "y": my+round(math.sin(angle)*spread), "dir": 180}
                    sprites.append({"uid": monster_uid, "id": monster_id, "type": 2, "attrs": deepcopy(attrs),
                                    "skillList": [integer(value) for value in monster.get("skill", "").split("#") if value], "entryIds": [],
                                    "labile": {"uid": monster_uid, "pos": point, "hp": {"max": hp, "cur": hp, "shield": 0}},
                                    "campId": 2, "brithPos": point})
            if sprites:
                waves.append(sprites)
        if not waves:
            fail("UNSUPPORTED_INSTANCE_WAVES", "No captured monster waves are available for this encounter")
        data = {"uid": uid, "refId": ref_id, "lv": level, "sprites": actors + deepcopy(waves[0]), "rewards": [],
                "startTime": self.now(), "players": [self.store._scene_player(state)]}
        active = {"version": 2, "kind": kind, "data": data, "damage": 0, "settled": False, "success": False,
                  "started": integer(self.store.instances[ref_id].get("timeType")) != 1,
                  "waves": waves, "waveIndex": 0, "createdTime": self.now(), "hitCount": 0}
        state["activeInstance"] = active
        return active

    def _expired(self, active):
        if active.get('practice'):return False
        ref = self.store.instances.get(integer(active["data"]["refId"]), {})
        seconds = integer(ref.get("time"))
        return active.get("started") and seconds > 0 and self.now() > integer(active["data"]["startTime"]) + seconds * 1000

    @staticmethod
    def _all_waves_dead(active):
        last_wave = integer(active.get("waveIndex")) >= len(active.get("waves", [[]])) - 1
        enemies = [s for s in active["data"]["sprites"] if s["type"] == 2]
        return bool(enemies) and last_wave and all(integer(s["labile"]["hp"]["cur"]) <= 0 for s in enemies)

    def _damage(self, state, payload):
        active = state.get("activeInstance")
        if not active:
            # Free-roam damage is client-authoritative in the recovered client.
            return False
        if active.get("settled") or active.get("left"):
            return False
        if self._expired(active):
            self._finish(state, active, success=False)
            return True
        sprites = {integer(s["uid"]): s for s in active["data"]["sprites"]}
        pushes, changed = [], False
        for supplied in payload.get("vo") or []:
            attacker = sprites.get(integer(supplied.get("atkSpriteId")))
            target = sprites.get(integer(supplied.get("tarSpriteId")))
            if not attacker or not target or attacker is target or integer(attacker["labile"]["hp"]["cur"]) <= 0:
                continue
            info = target["labile"]["hp"]
            if integer(info["cur"]) <= 0:
                continue
            raw = supplied.get("damage")
            if raw is None:
                raw = supplied.get("cdm")
            if raw is None:
                raw = finite(supplied.get("baseAtk", supplied.get("atk"))) * finite(supplied.get("fmd"), 1) * finite(supplied.get("sr"), 1) * finite(supplied.get("ul"), 1)
            requested = max(0, integer(finite(raw)))
            heal = bool(supplied.get("recHp"))
            if supplied.get("miss") and not heal:
                requested = 0
            if heal:
                actual = min(max(0, integer(info["max"]) - integer(info["cur"])), requested or max(0, integer(supplied.get("leech"))))
                info["cur"] += actual
            else:
                if attacker.get("campId") == target.get("campId"):
                    continue
                shield = min(max(0, integer(info.get("shield"))), requested)
                info["shield"] = max(0, integer(info.get("shield")) - shield)
                actual = min(integer(info["cur"]), max(0, requested - shield))
                info["cur"] -= actual
                if actual > 0 and target["type"] == 2:
                    active["damage"] += actual
                    if info["cur"] == 0 and not active.get('practice'):
                        kills = state.setdefault("progression", {}).setdefault("kills", {})
                        kills[str(target["id"])] = integer(kills.get(str(target["id"]))) + 1
                        if active.get('brawlSubId'):self.store.world.brawl_dead(state,active,target)
                        if active.get('stagePractice'):
                            counts=active['stageKills'];counts[str(target['id'])]=integer(counts.get(str(target['id'])))+1
                    if active.get("subId"):
                        boss, _ = self._boss(state, active["subId"])
                        pid = str(state["playerId"])
                        boss["scores"][pid] = integer(boss["scores"].get(pid)) + actual
            active["hitCount"] = integer(active.get("hitCount")) + 1
            vo = {**supplied, "atkSpriteId": attacker["uid"], "tarSpriteId": target["uid"], "refId": integer(supplied.get("refId"), attacker["id"]),
                  "damage": -actual if heal else actual, "dead": info["cur"] == 0}
            pushes.append({"vo": vo, "labile": deepcopy(target["labile"]), "playerId": [state["playerId"]]})
            changed = True
        if pushes:
            self._push(state, 50007, {"vo": pushes})
        if active.get("subId") and changed:
            sub_id = active["subId"]
            boss, _ = self._boss(state, sub_id)
            boss_id = integer(active.get("bountyRef", {}).get("bossMonster"))
            enemies = [s for s in active["data"]["sprites"] if s["type"] == 2 and (not boss_id or s["id"] == boss_id)]
            maximum = sum(integer(s["labile"]["hp"]["max"]) for s in enemies)
            remaining = sum(integer(s["labile"]["hp"]["cur"]) for s in enemies)
            boss["hpRate"] = max(0, min(10000, math.ceil(remaining * 10000 / maximum))) if maximum else 10000
            self._push(state, 52008, {"info": [self._boss_info(state, sub_id)[0]]})
            self._push(state, 52006, {**self._rank(state, sub_id), "playerId": state["playerId"]})
        if changed and all(s["labile"]["hp"]["cur"] <= 0 for s in active["data"]["sprites"] if s["type"] == 2):
            next_wave = integer(active.get("waveIndex")) + 1
            if next_wave < len(active.get("waves", [])):
                wave = deepcopy(active["waves"][next_wave])
                active["data"]["sprites"].extend(wave)
                active["waveIndex"] = next_wave
                self._push(state, 50003, {"addSprites": wave, "updateLabile": [], "remove": [], "pos": [], "playerId": state["playerId"]})
            elif not active.get('keepOpen'):
                self._finish(state, active)
        actors = [s for s in active["data"]["sprites"] if s["type"] == 1]
        if changed and active.get('stagePractice'):self.store.stages.publish(state,active)
        if actors and all(s["labile"]["hp"]["cur"] <= 0 for s in actors):
            active["defeated"] = True
            if not active.get('practice'):state["scene"]["dead"] = True
        return changed

    def _rng(self, state, active, label):
        seed = f"{state['playerId']}:{active['data']['uid']}:{label}".encode()
        return random.Random(int.from_bytes(hashlib.sha256(seed).digest()[:16], "big"))

    @staticmethod
    def _pick(rows, rng):
        weighted = [(r, max(0, integer(r.get("weight"), 1))) for r in rows]
        total = sum(weight for _, weight in weighted)
        if not total:
            fail("UNSUPPORTED_REWARD_GROUP", "Captured reward group has no positive weights")
        point = rng.randrange(total)
        for row, weight in weighted:
            point -= weight
            if point < 0:
                return row
        return weighted[-1][0]

    def _reward_items(self, encoded, rng):
        rewards = defaultdict(int)
        for entry in (encoded or "").split("#"):
            if not entry:
                continue
            bits = entry.split("_")
            if len(bits) < 3:
                fail("UNSUPPORTED_REWARD_ENCODING", f"Unsupported captured reward entry {entry}")
            kind, ref_id, count = map(integer, bits[:3])
            if count < 0 or count > 10000:
                fail("UNSUPPORTED_REWARD_COUNT", "Captured reward count exceeds the local resolver limit")
            if kind == 1 and len(bits) == 3:
                rewards[ref_id] += count
                continue
            if kind != 2:
                fail("UNSUPPORTED_REWARD_ENCODING", f"Unsupported captured reward type {kind}")
            chance = integer(bits[3], 10000) if len(bits) > 3 else 10000
            for _ in range(count):
                if rng.randrange(10000) >= max(0, min(10000, chance)):
                    continue
                row = self._pick(self.reward_groups.get(ref_id, []), rng)
                number = rng.randint(max(0, integer(row.get("min"))), max(0, integer(row.get("max"))))
                item_id = integer(row.get("itemId"))
                if not item_id:
                    item = self._pick(self.item_groups.get(integer(row.get("itemGroupId")), []), rng)
                    item_id = integer(item["itemRefId"])
                    number *= rng.randint(max(0, integer(item.get("min"))), max(0, integer(item.get("max"))))
                rewards[item_id] += number
        return {key: value for key, value in rewards.items() if value > 0}

    def _grant(self, state, encoded, active, label):
        rewards = self._reward_items(encoded, self._rng(state, active, label))
        for ref_id in rewards:
            if ref_id not in self.store.items and ref_id not in self.store.generals:
                fail("UNKNOWN_REWARD_ITEM", f"Captured reward resolves to unknown item {ref_id}")
        flat = "#".join(f"1_{ref_id}_{count}" for ref_id, count in sorted(rewards.items()))
        if flat:
            self.store._grant(state, flat)
        return [{"refId": ref_id, "count": count, "attrs": []} for ref_id, count in sorted(rewards.items())]

    def _instance_info(self, state, active):
        ref_id = active["data"]["refId"]
        return {"refId": ref_id, "lv": integer(state.setdefault("instanceLevels", {}).get(str(ref_id)), active["data"]["lv"])}

    def _finish(self, state, active, success=True):
        if active.get("settled"):
            return
        data = active["data"]
        row = self._instance_ref(data["refId"], data["lv"])
        reward = row.get("reward", "")
        if active.get('stagePractice'):
            definition=next((r for r in self.store.table('StageFbRef') if integer(r['refId'])==data['refId']),{})
            reward=definition.get('reward','')
        if active.get("subId") and success:
            ref = active["bountyRef"]
            group = integer(ref.get("rewardConfig"))
            rank_row = next((r for r in self.bounty_rewards[group] if integer(r["min"]) <= 1 <= integer(r["max"])), None)
            reward = rank_row.get("reward", "") if rank_row else ""
            if not rank_row:
                fail("NO_BOUNTY_REWARD", "No captured first-place reward is configured for this bounty")
        rewards = self._grant(state, reward, active, "completion") if success and not active.get('practice') else []
        data["rewards"] = rewards
        active.update(settled=True, success=bool(success), settledTime=self.now())
        if not active.get("subId") and success and not active.get('practice'):
            maximum = max((lv for ref_id, lv in self.store.instance_refs if ref_id == data["refId"]), default=data["lv"])
            state.setdefault("instanceLevels", {})[str(data["refId"])] = max(integer(state["instanceLevels"].get(str(data["refId"])), 1), min(maximum, data["lv"] + 1))
        if active.get("subId"):
            sub_id = active["subId"]
            boss, _ = self._boss(state, sub_id)
            if success:
                refresh = max(1, integer(self.subs[sub_id].get("time"), 1)) * 60000
                boss.update(hpRate=0, innerCount=0, nextRefreshTime=self.now() + refresh)
                boss["records"].insert(0, {"time": self.now(), "name": state["player"]["nickname"], "playerId": state["playerId"],
                                           "serverId": 1, "damage": integer(active["damage"])})
                del boss["records"][50:]
                self._push(state, 52004, {"subActivityId": sub_id, "rank": 1, "damage": integer(boss["scores"].get(str(state["playerId"]))), "reward": rewards,
                                         "playerId": state["playerId"], "times": 1,
                                         "neutrality": integer(self.subs[sub_id]["type"]) in (3, 6), "rebirthTime": boss["nextRefreshTime"]})
                self._push(state, 52008, {"info": [self._boss_info(state, sub_id)[0]]})
        else:
            self._push(state, 51003, {"data": data, "success": bool(success), "infos": self._instance_info(state, active)})
        self._archive(state, active)

    def _revive(self, state, payload):
        if payload.get("playerId") is not None and integer(payload["playerId"]) not in (0, integer(state["playerId"])):
            fail("WRONG_PLAYER", "Revival is limited to this offline captain")
        active = state.get("activeInstance")
        if not active:
            if not state.get("scene", {}).get("dead"):
                return False
            if not payload.get("free"):
                self.store._spend(state, self.store.global_config.get("rebirthCost", ""))
            state["scene"]["dead"] = False
            return True
        if payload.get("insUid") and integer(payload["insUid"]) != active["data"]["uid"]:
            fail("NO_ACTIVE_INSTANCE", "The revival request does not match this encounter")
        if active.get("settled"):
            fail("ENCOUNTER_ENDED", "This encounter has already ended")
        actors = [s for s in active["data"]["sprites"] if s["type"] == 1 and s.get("playerId") == state["playerId"]]
        if not any(s["labile"]["hp"]["cur"] <= 0 for s in actors):
            return False
        if not payload.get("free"):
            self.store._spend(state, self.store.global_config.get("rebirthCost", ""))
        for actor in actors:
            actor["labile"]["hp"]["cur"] = actor["labile"]["hp"]["max"]
            actor["labile"]["hp"]["shield"] = 0
        state["scene"]["dead"] = False
        active["defeated"] = False
        self._push(state, 50021, {"centerPos": deepcopy(actors[0]["labile"]["pos"]), "vos": [s["labile"] for s in actors], "playerId": state["playerId"]})
        return True

    def _sweep(self, state, cid, payload):
        ref_id = integer(payload.get("refId"))
        level = integer(payload.get("lv"), integer(state.get("instanceLevels", {}).get(str(ref_id)), 1))
        row = self._instance_ref(ref_id, level)
        count = integer(payload.get("count"), 1) if cid == 51007 else 1
        if not 1 <= count <= 100:
            fail("INVALID_SWEEP_COUNT", "Use a sweep count from 1 to 100")
        if self.store.instances[ref_id].get("type") == "10":
            fail("UNSUPPORTED_BOUNTY_SWEEP", "Pirate Bounties use their dedicated entry and settlement flow")
        if not state.get("settings", {}).get("fullGM"):
            if cid == 51007 and state["player"]["level"] < integer(self.store.global_config.get("insSweepLv"), 80):
                fail("SWEEP_LOCKED", "Player level does not meet the captured sweep requirement")
            if cid == 51051 and (not integer(row.get("openKill")) or self._crew_power(state) < integer(row.get("killPower"))):
                fail("QUICK_CLEAR_LOCKED", "Captured quick-clear requirements are not satisfied")
        encoded = row.get("switchReward" if cid == 51007 else "killReward") or row.get("reward", "")
        if not encoded:
            fail("NO_SWEEP_REWARD", "This captured instance has no sweep reward")
        self.store._spend(state, self.store.instances[ref_id].get("cost", ""), count)
        synthetic = {"data": {"uid": max(self.now() * 100, integer(state.get("lastEncounterUid")) + 100000)}}
        state["lastEncounterUid"] = synthetic["data"]["uid"]
        totals = defaultdict(int)
        for index in range(count):
            for item in self._grant(state, encoded, synthetic, f"sweep-{index}"):
                totals[item["refId"]] += item["count"]
        reward = [{"refId": key, "count": value, "attrs": []} for key, value in sorted(totals.items())]
        return {"rewards": reward} if cid == 51007 else {"reward": reward, "info": {"refId": ref_id, "lv": level}}

    def feature_audit(self, original_modules=None):
        """Conservative FnRef/protocol census; family binding is labelled heuristic."""
        modules = Path(original_modules) if original_modules else Path("/unavailable")
        enum = {}
        enum_file = next(modules.glob("0003_*"), None) if modules.exists() else None
        if enum_file:
            source = enum_file.read_text(encoding="utf-8")
            match = re.search(r"function\(e\)\{(.*?)\}\s*\(t\.EFnId", source, re.S)
            for name, value in re.findall(r'e\[e\.([A-Za-z0-9_$]+)=([\d.eE+]+)\]="', match.group(1) if match else ""):
                enum[integer(value)] = name
        implemented = set(self.store._implemented_ids()) | set(self.handled_ids)
        family_aliases = [("WorldBoss", ("WorldBoss",)), ("Ins", ("Ins",)), ("General", ("General",)),
                          ("Bag", ("Item", "Bag")), ("Equip", ("Equip",)), ("Pet", ("Pet",)), ("Mount", ("Mount",)),
                          ("Tower", ("Tower",)), ("Arena", ("Arena",)), ("Shop", ("Shop",)), ("Task", ("Task",)),
                          ("Guild", ("Guild",)), ("Friend", ("Friend",)), ("Email", ("Email",)),
                          ("Recruit", ("Lottery",)), ("Potential", ("Potential",)), ("Talent", ("Talent",)),
                          ("Voyage", ("Voyage",)), ("Gem", ("Gem",)), ("Ship", ("Ship",)), ("Skin", ("GeneralSkin", "Skin")),
                          ("Main", ("Scene", "Move", "Dead", "Create", "Damage", "Behavior", "Rebirth"))]
        features = []
        for ref_id, row in sorted(self.store.functions.items()):
            name = enum.get(ref_id, "")
            prefix = next((values for start, values in family_aliases if name.startswith(start)), (name,) if name else ())
            requests = [cid for cid, cmd in self.store.commands.items() if cmd.get("request") and prefix and cmd["name"].startswith(prefix)]
            missing = [cid for cid in requests if cid not in implemented]
            features.append({"fnId": ref_id, "enum": name, "name": self.store.english(row.get("name", "")),
                             "binding": "catalog-name-family-heuristic" if prefix else "unmapped-client-feature",
                             "requestIds": sorted(requests), "missingRequestIds": sorted(missing),
                             "status": "has-unimplemented-requests" if missing else "requests-covered-needs-ui-test" if requests else "client-only-or-unmapped"})
        bounty = sorted(cid for cid, cmd in self.store.commands.items() if cmd.get("request") and cmd["name"].startswith("WorldBoss"))
        return {"kind": "offline-feature-source-audit", "fnRefCount": len(features), "catalogCommands": len(self.store.commands),
                "encounterHandledIds": sorted(self.handled_ids), "features": features,
                "verifiedBountyRequestIds": bounty, "missingBountyRequestIds": sorted(set(bounty) - implemented),
                "originalClientDefectsFixed": [{"old": 50011, "correct": 50007, "reason": "Original DamageBc subscription uses 50007"},
                                               {"command": 52005, "requiredFields": ["subActivityId", "rankInfos", "myRank"], "oldFields": ["ranks", "records"]}],
                "limits": ["Feature-to-command family matching is conservative source metadata, not end-to-end UI coverage.",
                           "Damage arbitration and deterministic reward rolls are explicit local approximations.",
                           "No remote players, live payments, service endpoints or cross-account leaderboards are simulated."]}
