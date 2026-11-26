import hashlib
import json
import sqlite3
from pathlib import Path
from typing import TypeVar

from .models import Digest, Model

Record = TypeVar("Record", bound=Model)


def cache_key(*values) -> str:
    body = json.dumps(values, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=15)
        with self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            self.db.execute("CREATE TABLE IF NOT EXISTS digests (day TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def close(self) -> None:
        self.db.close()

    def get(self, key: str, kind: type[Record]) -> Record | None:
        row = self.db.execute("SELECT payload FROM cache WHERE key = ?", (key,)).fetchone()
        return kind.model_validate_json(row[0]) if row else None

    def put(self, key: str, value: Model) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO cache (key, payload) VALUES (?, ?)", (key, value.model_dump_json()))

    def get_digest(self, day: str) -> Digest | None:
        row = self.db.execute("SELECT payload FROM digests WHERE day = ?", (day,)).fetchone()
        return Digest.model_validate_json(row[0]) if row else None

    def put_digest(self, digest: Digest) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO digests (day, payload) VALUES (?, ?)",
                            (digest.date, digest.model_dump_json()))
