"""Local-only test identities. No external authentication or network dependencies."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import threading
import time


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    # Windows indexers can briefly hold a freshly written file. Retry the atomic
    # replacement only; never fall back to truncating an existing save in place.
    for attempt in range(6):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.01 * 2 ** attempt)


class OfflineAccounts:
    """Ten independent portable demo accounts with salted password hashes."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.runtime = self.root / "runtime"
        self.path = self.runtime / "accounts.json"
        self._lock = threading.RLock()
        self.session_path = self.runtime / "sessions.json"
        self._sessions: dict[str, tuple[str, float]] = {}
        if self.session_path.exists():
            records = json.loads(self.session_path.read_text(encoding="utf-8"))
            self._sessions = {key: (value[0], value[1]) for key, value in records.items() if value[1] > time.time()}
        self.initialize_demo_accounts()

    @staticmethod
    def _hash(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 240_000).hex()

    def _records(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def initialize_demo_accounts(self) -> list[dict]:
        with self._lock:
            if self.path.exists():
                return self.list_accounts()
            users, handout = {}, []
            alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
            for number in range(1, 11):
                username = f"pirate{number:02d}"
                password = "".join(secrets.choice(alphabet) for _ in range(16))
                salt = secrets.token_hex(16)
                users[username] = {"username": username, "displayName": f"Test Captain {number:02d}",
                                   "playerId": 9900000000000 + number, "salt": salt,
                                   "passwordHash": self._hash(password, salt), "gm": True}
                handout.append((username, password))
            # The plaintext list is explicitly requested for handing out local test copies.
            lines = ["PIRATES OFFLINE BROWSER — TEN LOCAL TEST LOGINS", "",
                     "These credentials work only with this offline package. They do not access the live game.",
                     "Each account has an independent local save and full offline GM access.",
                     "Each recipient runs their own copy; saves do not synchronize between computers.", "",
                     "Username          Password", "--------------------------------------"]
            lines.extend(f"{username:<18}{password}" for username, password in handout)
            lines += ["", "Keep this handout with the package. The server stores salted password hashes.",
                      "Do not use these test passwords on other services.", ""]
            (self.root / "TEST-LOGINS.txt").write_text("\n".join(lines), encoding="utf-8")
            atomic_json(self.path, {"version": 1, "localOnly": True, "users": users})
            return self.list_accounts()

    def list_accounts(self) -> list[dict]:
        return [{key: row[key] for key in ("username", "displayName", "playerId", "gm")}
                for row in self._records()["users"].values()]

    def public_account(self, username: str) -> dict:
        row = self._records()["users"].get(username)
        if row is None:
            raise KeyError("Unknown offline account")
        return {key: row[key] for key in ("username", "displayName", "playerId", "gm")}

    def login(self, username: str, password: str) -> dict | None:
        with self._lock:
            username = username.strip().lower()
            row = self._records()["users"].get(username)
            if not row or not hmac.compare_digest(self._hash(password, row["salt"]), row["passwordHash"]):
                return None
            token = secrets.token_urlsafe(32)
            self._sessions[hashlib.sha256(token.encode()).hexdigest()] = (username, time.time() + 24 * 3600)
            atomic_json(self.session_path, self._sessions)
            return {"token": token, "account": self.public_account(username), "playerId": row["playerId"]}

    def account_for_token(self, token: str | None) -> str | None:
        with self._lock:
            key = hashlib.sha256((token or "").encode()).hexdigest()
            session = self._sessions.get(key)
            if session and session[1] > time.time():
                return session[0]
            if self._sessions.pop(key, None):
                atomic_json(self.session_path, self._sessions)
            return None

    def logout(self, token: str | None) -> None:
        with self._lock:
            self._sessions.pop(hashlib.sha256((token or "").encode()).hexdigest(), None)
            atomic_json(self.session_path, self._sessions)
