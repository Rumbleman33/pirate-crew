"""Non-mutating, seeded draw experiments using captured or user-configured rules.

Captured crew recruitment is a two-stage table-weight model, not a promise of live
odds: server conditions and captured lucky/assigned-order rules are not applied.
No authoritative seasonal pool/odds/pity table was recovered. Halloween mode is
therefore explicitly an experiment requiring user-supplied prize weights.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import json
import math
from pathlib import Path
import random
import secrets


class DrawValidationError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def whole(value, name, low, high):
    if isinstance(value, bool):
        raise DrawValidationError("INVALID_INTEGER", f"{name} must be an integer from {low} to {high}")
    try:
        number = int(value)
        if Decimal(str(value)) != number or not low <= number <= high:
            raise ValueError
    except (ValueError, TypeError, InvalidOperation, OverflowError):
        raise DrawValidationError("INVALID_INTEGER", f"{name} must be an integer from {low} to {high}")
    return number


def weight(value):
    if isinstance(value, bool) or value is None or len(str(value)) > 64:
        raise DrawValidationError("INVALID_WEIGHT", "Supply a finite nonnegative weight for every prize")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DrawValidationError("INVALID_WEIGHT", "Weights must be finite nonnegative numbers")
    if not parsed.is_finite() or parsed < 0 or parsed > Decimal("1e12") or (parsed and parsed < Decimal("1e-12")):
        raise DrawValidationError("INVALID_WEIGHT", "Use zero or a weight from 1e-12 to 1e12")
    return Fraction(parsed)


def exact(value):
    return f"{value.numerator}/{value.denominator}"


def picker(values, weights):
    total = sum(weights, Fraction(0))
    if total <= 0:
        raise DrawValidationError("EMPTY_POOL", "At least one prize must have positive weight")
    denominator = math.lcm(*(value.denominator for value in weights))
    cumulative, running = [], 0
    for value in weights:
        running += value.numerator * (denominator // value.denominator)
        cumulative.append(running)
    def choose(rng):
        return values[bisect_right(cumulative, rng.randrange(running))]
    return choose


class OfflineDraws:
    def __init__(self, store):
        self.store = store
        self.root = Path(store.root)
        self.research, self.research_path = self._research()
        fresh = self.research.get("ordinaryRecruitmentTables", {})
        self.order_rows = deepcopy(fresh.get("LotteryGeneralOrderRef") or store.table("LotteryGeneralOrderRef"))
        self.general_rows = deepcopy(fresh.get("LotteryGeneralRef") or store.table("LotteryGeneralRef"))
        self._quality_weights = {whole(row["refId"], "quality", 1, 100): weight(row["weight"]) for row in self.order_rows}
        self._character_names = {}
        for gid, row in getattr(store, "generals", {}).items():
            value = row.get("generalName", row.get("name", str(gid)))
            self._character_names[int(gid)] = store.english(value) if hasattr(store, "english") else value

    def _research(self):
        for path in (self.root / "data/research/halloween-research.json", self.root / "data/halloween-research.json",
                     self.root.parent / "Pirates-Research-2026-10-29/halloween-research.json"):
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8")), path
        return {}, None

    def _source(self, captured=True):
        if not captured:
            return {"kind": "user-configured", "tables": [], "officialOdds": False,
                    "notes": "Prize membership, weights and guarantee settings are supplied by the user."}
        capture = self.research.get("capture", {})
        return {"kind": "captured-table-model", "tables": ["LotteryGeneralOrderRef", "LotteryGeneralRef"],
                "capturedAtUtc": capture.get("capturedAtUtc"), "clientVerCode": capture.get("clientVerCode"),
                "researchFile": "halloween-research.json" if self.research_path else None,
                "officialLiveOddsVerified": False,
                "selectionRule": "Choose an eligible quality by LotteryGeneralOrderRef.weight, then a member by LotteryGeneralRef.weight within the chosen group/quality."}

    @staticmethod
    def _public_entry(entry):
        return {key: deepcopy(value) for key, value in entry.items() if not key.startswith("_")}

    def _crew(self, group):
        by_quality = defaultdict(list)
        for row in self.general_rows:
            if whole(row["group"], "group", 1, 100) != group:
                continue
            quality = whole(row["order"], "quality", 1, 100)
            member_weight = weight(row["weight"])
            if member_weight <= 0 or self._quality_weights.get(quality, 0) <= 0:
                continue
            bounds = str(row.get("range", "")).split("#")
            if len(bounds) != 2:
                raise DrawValidationError("CORRUPT_CAPTURED_RANGE", "Captured fragment range must contain lower#upper")
            minimum, maximum = (whole(value, "fragment bound", 0, 1_000_000_000) for value in bounds)
            if minimum > maximum:
                raise DrawValidationError("CORRUPT_CAPTURED_RANGE", "Captured fragment lower bound exceeds upper bound")
            gid = whole(row["general"], "general ID", 1, 2_147_483_647)
            by_quality[quality].append({"id": f"crew-{group}-{row['refId']}", "refId": int(row["refId"]),
                                        "generalId": gid, "name": self._character_names.get(gid, str(gid)),
                                        "quality": quality, "minQuantity": minimum, "maxQuantity": maximum,
                                        "weight": float(member_weight), "asset": {"kind": "character", "id": gid},
                                        "_weight": member_weight})
        if not by_quality:
            raise DrawValidationError("UNKNOWN_POOL", f"No captured eligible crew entries for group {group}")
        eligible_total = sum((self._quality_weights[tier] for tier in by_quality), Fraction(0))
        original_total = sum(self._quality_weights.values(), Fraction(0))
        quality_ids, quality_weights, tiers, entries = [], [], [], []
        member_pickers = {}
        for quality in sorted(by_quality):
            rows = by_quality[quality]
            member_total = sum((entry["_weight"] for entry in rows), Fraction(0))
            quality_probability = self._quality_weights[quality] / eligible_total
            quality_ids.append(quality)
            quality_weights.append(self._quality_weights[quality])
            member_pickers[quality] = picker(rows, [entry["_weight"] for entry in rows])
            tiers.append({"quality": quality, "weight": float(self._quality_weights[quality]), "entryCount": len(rows),
                          "probability": float(quality_probability), "probabilityExact": exact(quality_probability)})
            for entry in rows:
                conditional = entry["_weight"] / member_total
                probability = quality_probability * conditional
                entry.update(probability=float(probability), probabilityExact=exact(probability),
                             qualityProbability=float(quality_probability), qualityProbabilityExact=exact(quality_probability),
                             withinQualityProbability=float(conditional), withinQualityProbabilityExact=exact(conditional),
                             _probability=probability)
                entries.append(entry)
        quality_picker = picker(quality_ids, quality_weights)
        def choose(rng):
            return member_pickers[quality_picker(rng)](rng)
        missing = [{"quality": tier, "weight": float(value), "originalProbability": float(value / original_total),
                    "originalProbabilityExact": exact(value / original_total)}
                   for tier, value in sorted(self._quality_weights.items()) if value > 0 and tier not in by_quality]
        missing_probability = sum((self._quality_weights[row["quality"]] / original_total for row in missing), Fraction(0))
        distribution = {"tiers": tiers, "conditionedOnEligibleQualities": bool(missing),
                        "eligibleQualities": sorted(by_quality), "missingQualityTiers": missing,
                        "missingOriginalProbability": float(missing_probability), "missingOriginalProbabilityExact": exact(missing_probability),
                        "qualityWeightDenominator": float(eligible_total), "originalQualityWeightDenominator": float(original_total)}
        return entries, choose, distribution

    def _starter_entries(self):
        entries = []
        for row in self.research.get("skins", []):
            skin_id = int(row.get("skinId", row.get("id")))
            entries.append({"id": str(skin_id), "itemId": skin_id, "name": row.get("nameEn", row.get("name", str(skin_id))),
                            "weight": None, "minQuantity": 1, "maxQuantity": 1,
                            "asset": {"kind": "skin", "id": skin_id},
                            "notes": "Captured Halloween content; membership in an official seasonal draw pool is not established."})
        return entries

    def catalog(self):
        pools = []
        crew_notes = ["Models the two captured weight stages only; full live draw odds have not been verified.",
                      "Quantities are sampled uniformly between the captured fragment bounds, inclusive; uniformity is a simulation assumption.",
                      "LotteryLuckyRef and LotteryAssignOrderRef guarantees and other server eligibility rules are not applied.",
                      "Results are statistics only. Captain inventory, currencies and saves are unchanged."]
        for group in (1, 2, 3):
            try:
                entries, _, distribution = self._crew(group)
            except DrawValidationError:
                continue
            pools.append({"id": f"crew-{group}", "title": f"Crew recruitment · captured group {group}",
                          "source": self._source(), "sourceKind": "captured-table-model",
                          "availableRules": ["two-stage-weight-selection", "inclusive-fragment-range", "seeded-independent-draws"],
                          "entries": [self._public_entry(value) for value in entries], "distribution": distribution,
                          "notes": crew_notes, "requiresUserWeights": False})
        pools.append({"id": "halloween-custom", "title": "Halloween · user-configured experiment",
                      "source": self._source(False), "sourceKind": "user-configured",
                      "availableRules": ["custom-prizes", "custom-weights", "custom-quantity-ranges", "optional-user-pity", "seeded-draws"],
                      "entries": self._starter_entries(), "requiresUserWeights": True,
                      "notes": ["No authoritative Halloween prize weights or pity rule were recovered.",
                                "Set your own prizes and weights before running this experiment. Empty weights are not filled with equal or official chances.",
                                "Starter skins identify captured Halloween content; they are not a confirmed official lottery pool.",
                                "SpecialItemSpiltRef contains fixed disassembly outputs and is not used as draw weights.",
                                "Optional guarantees are user-configured assumptions. Results do not alter any account."]})
        return pools

    def _custom(self, payload):
        raw = payload.get("entries")
        if raw is None and isinstance(payload.get("weights"), dict):
            raw = self._starter_entries()
            for entry in raw:
                entry["weight"] = payload["weights"].get(entry["id"], 0)
        if not isinstance(raw, list) or not 1 <= len(raw) <= 1000:
            raise DrawValidationError("CUSTOM_WEIGHTS_REQUIRED", "Supply 1–1000 prize entries with your own weights")
        entries, seen = [], set()
        for index, row in enumerate(raw):
            if not isinstance(row, dict):
                raise DrawValidationError("INVALID_ENTRY", "Every prize must be an object")
            key = str(row.get("id", row.get("itemId", ""))).strip()
            if not key or len(key) > 128 or key in seen:
                raise DrawValidationError("INVALID_ENTRY_ID", "Prize identifiers must be unique nonempty strings of at most 128 characters")
            seen.add(key)
            value = weight(row.get("weight"))
            minimum = whole(row.get("minQuantity", row.get("quantity", 1)), "minimum quantity", 0, 1_000_000_000)
            maximum = whole(row.get("maxQuantity", row.get("quantity", minimum)), "maximum quantity", 0, 1_000_000_000)
            if minimum > maximum:
                raise DrawValidationError("INVALID_RANGE", "Minimum prize quantity cannot exceed maximum")
            entry = {"id": key, "name": str(row.get("name", key))[:200], "weight": float(value),
                     "minQuantity": minimum, "maxQuantity": maximum, "_weight": value}
            if row.get("itemId") is not None:
                entry["itemId"] = whole(row["itemId"], "item ID", 1, 2_147_483_647)
            if isinstance(row.get("asset"), dict):
                entry["asset"] = {"kind": str(row["asset"].get("kind", ""))[:30], "id": str(row["asset"].get("id", ""))[:128]}
            image = row.get("image")
            if isinstance(image, str) and image.startswith("/") and not image.startswith("//") and len(image) <= 500:
                entry["image"] = image
            entries.append(entry)
        total = sum((entry["_weight"] for entry in entries), Fraction(0))
        if total <= 0:
            raise DrawValidationError("EMPTY_POOL", "At least one custom prize needs a positive weight")
        for entry in entries:
            probability = entry["_weight"] / total
            entry.update(probability=float(probability), probabilityExact=exact(probability), _probability=probability)
        return entries, picker(entries, [entry["_weight"] for entry in entries]), {"tiers": [], "conditionedOnEligibleQualities": False, "missingQualityTiers": []}

    @staticmethod
    def _pity(raw, entries):
        if raw is None or raw is False:
            return None, None
        if not isinstance(raw, dict):
            raise DrawValidationError("INVALID_PITY", "Guarantee settings must be an object or omitted")
        every = whole(raw.get("every"), "guarantee interval", 1, 10000)
        target_ids = raw.get("targetIds")
        if not isinstance(target_ids, list) or not target_ids:
            raise DrawValidationError("INVALID_PITY", "Select at least one guaranteed prize identifier")
        target_ids = list(dict.fromkeys(str(value) for value in target_ids))
        available = {entry["id"] for entry in entries}
        if not set(target_ids) <= available:
            raise DrawValidationError("INVALID_PITY", "Every guaranteed prize must be present in this custom pool")
        targets = [entry for entry in entries if entry["id"] in target_ids]
        target_weight = sum((entry["_weight"] for entry in targets), Fraction(0))
        if target_weight <= 0:
            raise DrawValidationError("INVALID_PITY", "Guaranteed prizes need a positive combined weight")
        reset = raw.get("resetOnNatural", True)
        if not isinstance(reset, bool):
            raise DrawValidationError("INVALID_PITY", "resetOnNatural must be true or false")
        return {"every": every, "targetIds": target_ids, "resetOnNatural": reset,
                "mode": "consecutive-misses" if reset else "fixed-cadence",
                "sourceKind": "user-configured", "officialRule": False}, picker(targets, [entry["_weight"] for entry in targets])

    @staticmethod
    def _expected_forced(pulls, pity, target_probability):
        if not pity:
            return 0.0
        interval = pity["every"]
        if not pity["resetOnNatural"]:
            return float(pulls // interval)
        q = 1.0 - float(target_probability)
        uninterrupted_misses = q ** (interval - 1)
        force_probabilities = [0.0] * (pulls + 1)
        total = 0.0
        for draw in range(interval, pulls + 1):
            last_reset = draw - interval
            reset_probability = 1.0 if last_reset == 0 else float(target_probability) + q * force_probabilities[last_reset]
            force_probabilities[draw] = uninterrupted_misses * reset_probability
            total += force_probabilities[draw]
        return total

    def simulate(self, payload):
        if not isinstance(payload, dict):
            return {"ok": False, "error": {"code": "INVALID_PAYLOAD", "message": "Draw experiment payload must be an object"}, "inventoryChanged": False}
        try:
            pool_id = str(payload.get("poolId", "crew-1"))
            pulls = whole(payload.get("pulls", 10), "pulls", 1, 10000)
            seed = payload.get("seed")
            if seed is None or seed == "":
                seed = secrets.token_hex(8)
            if isinstance(seed, bool) or not isinstance(seed, (int, str)) or len(str(seed)) > 200:
                raise DrawValidationError("INVALID_SEED", "Seed must be a string or integer of at most 200 characters")
            rng = random.Random(seed)
            if pool_id in ("crew-1", "crew-2", "crew-3"):
                if payload.get("pity"):
                    raise DrawValidationError("UNMODELED_CAPTURED_PITY", "Captured crew mode does not implement unverified guarantee rules; use a user-configured experiment")
                entries, choose, distribution = self._crew(int(pool_id[-1]))
                captured = True
                pity, guarantee_picker = None, None
            elif pool_id == "halloween-custom":
                entries, choose, distribution = self._custom(payload)
                captured = False
                pity, guarantee_picker = self._pity(payload.get("pity"), entries)
            else:
                raise DrawValidationError("UNKNOWN_POOL", "Select crew-1, crew-2, crew-3 or halloween-custom")
            targets = set(pity["targetIds"]) if pity else set()
            target_probability = sum((entry["_probability"] for entry in entries if entry["id"] in targets), Fraction(0))
            forced_expectation = self._expected_forced(pulls, pity, target_probability)
            target_weight = sum((entry["_weight"] for entry in entries if entry["id"] in targets), Fraction(0))
            aggregates = {}
            for entry in entries:
                forced_share = float(entry["_weight"] / target_weight) if entry["id"] in targets else 0.0
                expected = float(entry["_probability"]) * (pulls - forced_expectation) + forced_share * forced_expectation
                average_quantity = Fraction(entry["minQuantity"] + entry["maxQuantity"], 2)
                public = self._public_entry(entry)
                public.update(expectedHits=expected, expectedQuantity=expected * float(average_quantity),
                              baseExpectedHits=float(entry["_probability"] * pulls))
                if not pity:
                    public["expectedHitsExact"] = exact(entry["_probability"] * pulls)
                    public["expectedQuantityExact"] = exact(entry["_probability"] * pulls * average_quantity)
                aggregates[entry["id"]] = {**public, "hits": 0, "totalQuantity": 0, "pityHits": 0}
            trace, counter, forced_count, quantity_total = [], 0, 0, 0
            for draw in range(1, pulls + 1):
                forced = bool(pity and counter >= pity["every"] - 1)
                entry = guarantee_picker(rng) if forced else choose(rng)
                amount = rng.randint(entry["minQuantity"], entry["maxQuantity"])
                aggregate = aggregates[entry["id"]]
                aggregate["hits"] += 1
                aggregate["totalQuantity"] += amount
                aggregate["pityHits"] += int(forced)
                forced_count += int(forced)
                quantity_total += amount
                if pity:
                    counter = 0 if forced or (pity["resetOnNatural"] and entry["id"] in targets) else counter + 1
                if len(trace) < 200:
                    trace.append({"draw": draw, "id": entry["id"], "name": entry["name"], "quantity": amount,
                                  "quality": entry.get("quality"), "forcedByUserPity": forced})
            distribution["entries"] = [{key: value for key, value in aggregate.items() if key not in ("hits", "totalQuantity", "pityHits")} for aggregate in aggregates.values()]
            notes = ["This is a local statistical experiment. No inventory, currency, login or save was changed.",
                     "The seed reproduces this simulator's results; it does not predict a live server's random generator."]
            if captured:
                notes += ["Two-stage table selection only; server lucky/assigned-order rules and other eligibility conditions are not modeled.",
                          "Fragment quantities use a uniform integer choice within captured inclusive bounds; uniformity is a simulator assumption."]
                if distribution["conditionedOnEligibleQualities"]:
                    notes.append("Some captured quality tiers have no eligible members in this group. Their missing probability is reported, and the experiment explicitly conditions on represented tiers.")
            else:
                notes += ["All prize weights and guarantee rules are user-configured; these are not official Halloween odds.",
                          "No seasonal probability/pity table was recovered. Fixed disassembly outputs are never used as draw weights."]
                if pity:
                    notes.append("Displayed base probabilities apply to ordinary draws; expected counts also include the user-configured guarantee.")
            return {"ok": True, "poolId": pool_id, "pulls": pulls, "seed": seed,
                    "sourceKind": "captured-table-model" if captured else "user-configured", "source": self._source(captured),
                    "fidelity": "Captured crew weight model, unverified live guarantees" if captured else "User-configured experiment; official seasonal odds unknown",
                    "notes": notes, "distribution": distribution,
                    "results": sorted(aggregates.values(), key=lambda value: (-value["hits"], value["id"])),
                    "totals": {"draws": pulls, "totalQuantity": quantity_total, "uniqueResults": sum(value["hits"] > 0 for value in aggregates.values()),
                               "pityHits": forced_count, "expectedPityHits": forced_expectation},
                    "draws": trace, "drawsTruncated": pulls > len(trace), "pity": pity, "inventoryChanged": False}
        except (DrawValidationError, InvalidOperation) as error:
            return {"ok": False, "error": {"code": getattr(error, "code", "INVALID_PARAMETERS"), "message": str(error)}, "inventoryChanged": False}
