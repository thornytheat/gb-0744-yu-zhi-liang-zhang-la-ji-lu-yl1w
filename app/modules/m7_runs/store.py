import json
import sqlite3
from contextlib import closing
from pathlib import Path


class History:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS calculations (code TEXT PRIMARY KEY, result TEXT NOT NULL)"
            )

    def connect(self):
        return sqlite3.connect(self.path, timeout=8)

    def find(self, code):
        with closing(self.connect()) as db:
            row = db.execute("SELECT result FROM calculations WHERE code=?", (code,)).fetchone()
            return json.loads(row[0]) if row else None

    def publish(self, code, result):
        with closing(self.connect()) as db, db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO calculations VALUES (?,?)",
                (code, json.dumps(result, ensure_ascii=False)),
            )
            payload = db.execute("SELECT result FROM calculations WHERE code=?", (code,)).fetchone()[0]
            return json.loads(payload), not cursor.rowcount

    def recent(self):
        with closing(self.connect()) as db:
            return [
                json.loads(row[0])["清单"]
                for row in db.execute("SELECT result FROM calculations ORDER BY rowid DESC LIMIT 50")
            ]
