"""Durable, process-exclusive accounting for the DS-PILOT-02 experiment."""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import pwd
import sqlite3
import stat

EXPERIMENT = "DS-PILOT-02"
LIMIT = 100_000  # integer micro-USD
RESERVE = 7_080
MAX_ATTEMPTS = 12


def canonical_path():
    return Path(pwd.getpwuid(os.getuid()).pw_dir) / ".local/state/ds-consultant/paid-budget.sqlite"


def utc():
    return datetime.now(timezone.utc).isoformat()


class PaidLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        parent = self.path.parent.stat()
        if parent.st_uid != os.getuid() or parent.st_mode & 0o022:
            raise ValueError("Unsafe paid ledger directory.")
        self.fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            status = os.fstat(self.fd)
            if not stat.S_ISREG(status.st_mode) or status.st_uid != os.getuid() or status.st_nlink != 1:
                raise ValueError("Unsafe paid ledger file.")
            os.fchmod(self.fd, 0o600)
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.transaction() as db:
                db.execute("""CREATE TABLE IF NOT EXISTS experiment (
                    id TEXT PRIMARY KEY CHECK(id='DS-PILOT-02'), blocked INTEGER NOT NULL DEFAULT 0)""")
                db.execute("INSERT OR IGNORE INTO experiment(id) VALUES (?)", (EXPERIMENT,))
                db.execute("""CREATE TABLE IF NOT EXISTS attempts (
                    request TEXT PRIMARY KEY, state TEXT NOT NULL,
                    reserved_utc TEXT NOT NULL, dispatch_utc TEXT, finished_utc TEXT,
                    model TEXT, provider_id TEXT, prompt_tokens INTEGER, cache_hit_tokens INTEGER,
                    cache_miss_tokens INTEGER, completion_tokens INTEGER, estimate INTEGER,
                    finish_reason TEXT, error TEXT)""")
                # Preserve the full reservation even for a crash before dispatch.
                db.execute("""UPDATE attempts SET state='unknown', error='interrupted', finished_utc=?
                    WHERE state IN ('reserved','dispatch_intent')""", (utc(),))
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    @contextmanager
    def transaction(self):
        if self.fd is None:
            raise ValueError("Paid ledger closed.")
        with closing(sqlite3.connect(self.path, timeout=3)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA synchronous=FULL")
            with db:
                db.execute("BEGIN IMMEDIATE")
                yield db

    def _summary(self, db):
        totals = db.execute("""SELECT count(*) slots, count(dispatch_utc) intents,
            COALESCE(sum(estimate),0) known,
            count(CASE WHEN state != 'usage_reconciled' THEN 1 END) pending
            FROM attempts""").fetchone()
        blocked = bool(db.execute("SELECT blocked FROM experiment WHERE id=?", (EXPERIMENT,)).fetchone()[0])
        risk = totals["pending"] * RESERVE
        remaining = max(0, LIMIT - risk - totals["known"])
        return dict(experiment=EXPERIMENT, authorized_micro_usd=LIMIT, per_request_micro_usd=RESERVE,
                    reserved_micro_usd=totals["slots"] * RESERVE, at_risk_micro_usd=risk,
                    usage_estimate_micro_usd=totals["known"], remaining_micro_usd=remaining,
                    dispatch_intents=totals["intents"], blocked=blocked,
                    remaining_calls=0 if blocked else min(MAX_ATTEMPTS - totals["slots"], remaining // RESERVE))

    def summary(self):
        with self.transaction() as db:
            return self._summary(db)

    def reserve(self, request):
        with self.transaction() as db:
            if not self._summary(db)["remaining_calls"]:
                raise ValueError("Paid experiment limit reached.")
            if db.execute("""SELECT 1 FROM attempts WHERE request=?
                    OR state IN ('reserved','dispatch_intent')""", (request,)).fetchone():
                raise ValueError("Duplicate or pending paid request.")
            db.execute("INSERT INTO attempts(request,state,reserved_utc) VALUES (?,'reserved',?)", (request, utc()))

    def intent(self, request):
        with self.transaction() as db:
            if db.execute("""UPDATE attempts SET state='dispatch_intent',dispatch_utc=?
                    WHERE request=? AND state='reserved'""", (utc(), request)).rowcount != 1:
                raise ValueError("Paid reservation unavailable.")

    def unknown(self, request, error, *, block=False):
        with self.transaction() as db:
            db.execute("""UPDATE attempts SET state='unknown',error=?,finished_utc=?
                WHERE request=? AND state IN ('reserved','dispatch_intent')""", (error, utc(), request))
            if block:
                db.execute("UPDATE experiment SET blocked=1")

    def reconcile(self, request, model, provider_id, usage, finish_reason):
        prompt, hit, miss, output = usage
        # Ceiling of fractional micro-USD, at peak official prices.
        estimate = (miss * 300 + hit * 6 + output * 1200 + 999) // 1000
        anomaly = prompt > 10000 or output > 450 or estimate > RESERVE
        with self.transaction() as db:
            changed = db.execute("""UPDATE attempts SET state='usage_reconciled', finished_utc=?,
                model=?,provider_id=?,prompt_tokens=?,cache_hit_tokens=?,cache_miss_tokens=?,
                completion_tokens=?,estimate=?,finish_reason=?,error=?
                WHERE request=? AND state='dispatch_intent'""",
                (utc(), model, provider_id, prompt, hit, miss, output, estimate, finish_reason,
                 "usage_bound_exceeded" if anomaly else None, request)).rowcount
            if changed != 1:
                raise ValueError("Invalid ledger transition.")
            if anomaly:
                db.execute("UPDATE experiment SET blocked=1")
        return not anomaly

    def receipt(self, request):
        with self.transaction() as db:
            row = db.execute("""SELECT state,dispatch_utc,model,provider_id AS model_request_id,
                prompt_tokens,cache_hit_tokens,cache_miss_tokens,completion_tokens,
                estimate AS usage_estimate_micro_usd,finish_reason,error FROM attempts WHERE request=?""",
                (request,)).fetchone()
            return dict(row, attempts=int(row["dispatch_utc"] is not None)) if row else {"attempts": 0}
