"""English presentation of captured tables without altering protocol values."""
from functools import lru_cache
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
CJK = re.compile(r"[\u3400-\u9fff]")


@lru_cache(maxsize=1)
def dictionary():
    result = {}
    for path in (ROOT / "public/game/i18n/en.json", ROOT / "public/english-extra.json", ROOT / "public/offline-english-extra.json"):
        if path.exists():
            result.update(json.loads(path.read_text(encoding="utf-8")))
    return result


def english(value):
    if not isinstance(value, str):
        return value
    pack = dictionary()
    if value in pack:
        translated = pack[value]
        return pack.get(translated, translated)
    if not CJK.search(value):
        return value
    if value.startswith(("[", "{")):
        try:
            def walk(item):
                if isinstance(item, list):
                    return [walk(child) for child in item]
                if isinstance(item, dict):
                    return {key: walk(child) for key, child in item.items()}
                return english(item)
            return json.dumps(walk(json.loads(value)), ensure_ascii=False, separators=(",", ":"))
        except (ValueError, TypeError):
            pass
    match = re.fullmatch(r"兔碗解锁(\d+)", value)
    if match:
        return "Udon unlock " + match[1]
    match = re.fullmatch(r"(乌塔|史基)-专属-效果(\d+)", value)
    if match:
        return ("Uta" if match[1] == "乌塔" else "Shiki") + ": exclusive effect " + match[2]
    return value


def display_row(table, row):
    result = {key: english(value) for key, value in row.items()}
    if table == "CmdCodeRef" and row.get("enName"):
        result["name"] = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", row["enName"].replace("_", " "))
    return result
