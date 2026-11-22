"""张拉证据凭据的持久化。

一个「班次」最多只有一份处于「有效」状态的凭据，由部分唯一索引兜底。
凭据一经签发即冻结当时的读数与结论；撤回只改状态、不删除记录，
因此监理按原凭据号仍能查到签收时的依据。补签生成新凭据号，绝不沿用原号。
"""

import json
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

PENDING = "待签"
VALID = "有效"
REVOKED = "撤回"
STATUSES = (PENDING, VALID, REVOKED)

SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_receipts (
    serial          TEXT PRIMARY KEY,
    run_code        TEXT NOT NULL,
    status          TEXT NOT NULL,
    issued_at       TEXT NOT NULL,
    issued_by       TEXT NOT NULL,
    supersedes      TEXT,
    snapshot        TEXT NOT NULL,
    snapshot_digest TEXT NOT NULL,
    revoked_at      TEXT,
    revoked_by      TEXT,
    revoke_reason   TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS evidence_one_valid_per_run
    ON evidence_receipts(run_code) WHERE status = '有效';
CREATE INDEX IF NOT EXISTS evidence_receipts_by_run
    ON evidence_receipts(run_code);
"""


def utcnow():
    return datetime.now(timezone.utc)


def stamp(moment=None):
    return (moment or utcnow()).isoformat(timespec="seconds")


def digest(payload):
    return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


class EvidenceStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.executescript(SCHEMA)

    def connect(self):
        # isolation_level=None 让写操作用显式 BEGIN IMMEDIATE 串行化，
        # 两人同时提交签发/撤回时只会有一笔生效。
        db = sqlite3.connect(self.path, timeout=8, isolation_level=None)
        db.row_factory = sqlite3.Row
        return db

    # ---- 读取 -------------------------------------------------------------

    @staticmethod
    def _record(row):
        return {
            "凭据号": row["serial"],
            "班次": row["run_code"],
            "状态": row["status"],
            "签发时间": row["issued_at"],
            "签发人": row["issued_by"],
            "替代凭据": row["supersedes"],
            "依据摘要": row["snapshot_digest"],
            "撤回时间": row["revoked_at"],
            "撤回人": row["revoked_by"],
            "撤回原因": row["revoke_reason"],
            "快照": json.loads(row["snapshot"]),
        }

    def find(self, serial):
        with closing(self.connect()) as db:
            row = db.execute("SELECT * FROM evidence_receipts WHERE serial=?", (serial,)).fetchone()
        return self._record(row) if row else None

    def history(self, run_code):
        """同一班次的全部凭据，最新的在前。撤回的凭据也留在历史里。"""
        with closing(self.connect()) as db:
            rows = db.execute(
                "SELECT * FROM evidence_receipts WHERE run_code=? ORDER BY rowid DESC", (run_code,)
            ).fetchall()
        return [self._record(row) for row in rows]

    def current(self, run_code):
        with closing(self.connect()) as db:
            row = db.execute(
                "SELECT * FROM evidence_receipts WHERE run_code=? AND status=?",
                (run_code, VALID),
            ).fetchone()
        return self._record(row) if row else None

    def latest(self, run_code):
        with closing(self.connect()) as db:
            row = db.execute(
                "SELECT * FROM evidence_receipts WHERE run_code=? ORDER BY rowid DESC LIMIT 1",
                (run_code,),
            ).fetchone()
        return self._record(row) if row else None

    def status_for(self, run_code):
        current = self.current(run_code)
        if current:
            return VALID
        latest = self.latest(run_code)
        return REVOKED if latest else PENDING

    def statuses(self, run_codes):
        codes = list(run_codes)
        if not codes:
            return {}
        placeholders = ",".join("?" for _ in codes)
        with closing(self.connect()) as db:
            valid = {
                row["run_code"]
                for row in db.execute(
                    f"SELECT run_code FROM evidence_receipts WHERE status='有效' AND run_code IN ({placeholders})",
                    codes,
                )
            }
            touched = {
                row["run_code"]
                for row in db.execute(
                    f"SELECT run_code FROM evidence_receipts WHERE run_code IN ({placeholders})",
                    codes,
                )
            }
        return {code: VALID if code in valid else REVOKED if code in touched else PENDING for code in codes}

    # ---- 写入 -------------------------------------------------------------

    def _mint(self, db, run_code, moment):
        prefix = f"EV-{moment.strftime('%Y%m%d')}-{run_code[:6].upper()}-"
        for _ in range(12):
            serial = prefix + secrets.token_hex(3).upper()
            if not db.execute("SELECT 1 FROM evidence_receipts WHERE serial=?", (serial,)).fetchone():
                return serial
        return prefix + secrets.token_hex(8).upper()

    def issue(self, run_code, snapshot, actor, moment=None):
        """签发或补签。

        已有有效凭据时直接返回它（重试不新增记录）；否则新建一份凭据。
        若此前有撤回记录，则把最新一份记为「被替代」，但仍原样保留。
        """
        moment = moment or utcnow()
        payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
        snapshot_digest = digest(snapshot)
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                current = db.execute(
                    "SELECT * FROM evidence_receipts WHERE run_code=? AND status=?",
                    (run_code, VALID),
                ).fetchone()
                if current is not None:
                    db.execute("COMMIT")
                    return self._record(current), False
                previous = db.execute(
                    "SELECT serial FROM evidence_receipts WHERE run_code=? ORDER BY rowid DESC LIMIT 1",
                    (run_code,),
                ).fetchone()
                serial = self._mint(db, run_code, moment)
                db.execute(
                    "INSERT INTO evidence_receipts"
                    " (serial, run_code, status, issued_at, issued_by, supersedes, snapshot, snapshot_digest)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (
                        serial,
                        run_code,
                        VALID,
                        stamp(moment),
                        actor,
                        previous["serial"] if previous else None,
                        payload,
                        snapshot_digest,
                    ),
                )
                row = db.execute("SELECT * FROM evidence_receipts WHERE serial=?", (serial,)).fetchone()
                db.execute("COMMIT")
                return self._record(row), True
            except Exception:
                db.execute("ROLLBACK")
                raise

    def revoke(self, run_code, actor, reason, moment=None):
        """撤回当前有效凭据。

        已无有效凭据时幂等返回最近一份（含撤回记录），不会新增签发记录；
        从未签发过则抛 LookupError，交由调用方转成 404。
        """
        moment = moment or utcnow()
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                current = db.execute(
                    "SELECT * FROM evidence_receipts WHERE run_code=? AND status=?",
                    (run_code, VALID),
                ).fetchone()
                if current is not None:
                    db.execute(
                        "UPDATE evidence_receipts SET status=?, revoked_at=?, revoked_by=?, revoke_reason=?"
                        " WHERE serial=?",
                        (REVOKED, stamp(moment), actor, reason, current["serial"]),
                    )
                    row = db.execute(
                        "SELECT * FROM evidence_receipts WHERE serial=?", (current["serial"],)
                    ).fetchone()
                    db.execute("COMMIT")
                    return self._record(row), True
                latest = db.execute(
                    "SELECT * FROM evidence_receipts WHERE run_code=? ORDER BY rowid DESC LIMIT 1",
                    (run_code,),
                ).fetchone()
                db.execute("COMMIT")
                if latest is None:
                    raise LookupError(run_code)
                return self._record(latest), False
            except LookupError:
                raise
            except Exception:
                db.execute("ROLLBACK")
                raise
