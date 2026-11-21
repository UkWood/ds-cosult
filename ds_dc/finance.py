"""Private, process-safe operation ledger. Amounts are integer microdollars."""
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, ROUND_CEILING
import fcntl
import json
import os
from pathlib import Path
import tempfile
import time
from zoneinfo import ZoneInfo

from .context import OUTPUT
from .provider_failure import ProviderFailure

RATES = {"miss": "0.30", "hit": "0.006", "completion": "1.20", "page": "225"}
PUBLIC = {"month": 30_000_000, "day": 2_000_000, "peer_day": 500_000, "warning": 24_000_000}
OWNER = {"budget": 2_500_000, "reserve_disabled": 500_000,
         "normal": 24, "extended": 8, "chats": 32, "pages": 1000,
         "upload": 28, "status": 28, "delete": 28, "calibration": 2}
CHAT_MODES = {"normal", "extended", "calibration"}


class Stopped(ValueError):
    """Expected admission failure with a safe status code."""


def token_cost(prompt, hit, output):
    return int((Decimal(RATES["miss"]) * (prompt - hit) + Decimal(RATES["hit"]) * hit
                + Decimal(RATES["completion"]) * output).to_integral_value(rounding=ROUND_CEILING))


def cold_cost(bound):
    return token_cost(bound, 0, OUTPUT)


def local_day(now):
    return datetime.fromtimestamp(now, ZoneInfo("Europe/Moscow")).date().isoformat()


class Ledger:
    def __init__(self, directory):
        self.path = Path(directory)
        self.path.mkdir(exist_ok=True, parents=True, mode=0o700)
        if self.path.is_symlink() or self.path.stat().st_mode & 0o077:
            raise ValueError("ledger_directory_must_be_private")
        self.file = self.path / "ledger.json"

    def save(self, state):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path,
                                         prefix=".pending-", delete=False) as out:
            json.dump(state, out, ensure_ascii=True, separators=(",", ":"))
            out.flush()
            os.fsync(out.fileno())
        os.replace(out.name, self.file)
        fd = os.open(self.path, os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    @contextmanager
    def transaction(self, *, maintain=True):
        with (self.path / ".lock").open("a+b") as lock:
            os.fchmod(lock.fileno(), 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = json.loads(self.file.read_text()) if self.file.exists() else {
                "operations": {}, "bindings": {}, "runs": {}}
            if not maintain:
                yield state
                return
            for path in self.path.glob(".pending-*"):
                path.unlink()
            interrupted = False
            for row in state["operations"].values():
                if row["state"] == "inflight":
                    row["state"] = "unknown"
                    interrupted = True
                elif row["state"] == "reserved":
                    row["state"] = "cancelled"
                    interrupted = True
            cutoff = time.time() - 30 * 86400
            stale = [key for key, binding in state["bindings"].items() if binding["expires"] <= cutoff]
            for key in stale:
                del state["bindings"][key]
            pruned = False
            events = state.get("recovery_events")
            original_run = None
            if events:
                key = events[0]["authorization"]["original_operation"]
                original_run = state["operations"][key]["run"]
            for row in state["operations"].values():
                if original_run is not None and row["run"] == original_run:
                    continue
                if row.get("utc", float("inf")) <= cutoff:
                    row.pop("usage", None)
                    row.pop("calibration_result", None)
                    row.pop("utc", None)
                    pruned = True
            if interrupted or stale or pruned:
                self.save(state)
            yield state

    @staticmethod
    def accounted(row):
        if row["state"] == "cancelled":
            return 0
        if row["state"] == "settled":
            return row["cost"]
        return max(row.get("cost", 0), row["reserve"])

    def reserve(self, state, run, permit_sha, peer, now, limits, ops, *, public=False, campaign=None, recovery=None):
        if state["runs"].get(run, permit_sha) != permit_sha:
            raise Stopped("go_changed")
        existing = list(state["operations"].values())
        ignored = None
        if recovery:
            from .recovery import ORIGINAL_UPLOAD
            if public or campaign != "dc02-live" or not state.get("recovery_events") or (
                    recovery["original_operation"] != ORIGINAL_UPLOAD):
                raise Stopped("invalid_recovery_authorization")
            ignored = ORIGINAL_UPLOAD
        if any(key != ignored and row["state"] == "unknown"
               and row.get("profile") == ("public" if public else "owner")
               for key, row in state["operations"].items()):
            raise Stopped("provider_unknown")
        if any(key in state["operations"] for key in ops):
            raise Stopped("duplicate_operation")
        day = local_day(now)
        new = {key: dict(row, state="reserved", run=run, day=day, utc=now, peer=peer,
                         profile="public" if public else "owner", campaign=campaign) for key, row in ops.items()}
        all_rows = [row for row in existing if row["state"] != "cancelled"] + list(new.values())
        def exceeds(rows, caps):
            counts = {kind: sum(row["kind"] == kind for row in rows) for kind in (
                "normal", "extended", "calibration", "upload", "status", "delete")}
            return (sum(map(self.accounted, rows)) > caps["budget"]
                    or sum(row.get("pages", 0) for row in rows) > caps["pages"]
                    or sum(counts[kind] for kind in CHAT_MODES) > caps["chats"]
                    or any(counts[kind] > caps[kind] for kind in counts)
                    or any(sum(row.get("slot", row["kind"]) == kind for row in rows) > caps[kind]
                           for kind in ("normal", "extended")))
        if exceeds([row for row in all_rows if row["run"] == run], limits):
            raise Stopped("budget_exhausted")
        if campaign and exceeds([row for row in all_rows if row.get("campaign") == campaign], OWNER):
            raise Stopped("campaign_budget_exhausted")
        if recovery:
            cal_rows = [row for key, row in (state["operations"] | new).items()
                        if key.startswith("dc02-live/calibration/") and row["state"] != "cancelled"]
            cal_caps = OWNER | {"budget": 783_300, "pages": 548, "upload": 15, "chats": 2}
            if exceeds(cal_rows, cal_caps) or sum(row["reserve"] for row in cal_rows) > cal_caps["budget"]:
                raise Stopped("recovery_budget_exhausted")
        if public:
            rows_public = [r for r in all_rows if r["profile"] == "public"]
            if (sum(self.accounted(r) for r in rows_public if r["day"][:7] == day[:7]) > PUBLIC["month"]
                    or sum(self.accounted(r) for r in rows_public if r["day"] == day) > PUBLIC["day"]
                    or sum(self.accounted(r) for r in rows_public if r["day"] == day and r["peer"] == peer)
                    > PUBLIC["peer_day"]):
                raise Stopped("budget_exhausted")
        state["runs"][run] = permit_sha
        state["operations"].update(new)
        if recovery and recovery.get("consumption"):
            state["recovery_events"].append(recovery["consumption"])
        self.save(state)

    def operate(self, state, key, call, interpret):
        row = state["operations"][key]
        row["state"] = "inflight"
        self.save(state)
        started = time.monotonic()
        returned = False
        result = None
        try:
            result = call()
            returned = True
            cost, facts = interpret(result)
            if type(cost) is not int or cost < 0:
                raise ProviderFailure("financial_accounting", "invalid_cost")
        except Exception as error:
            if isinstance(error, ProviderFailure):
                failure = error
            elif returned and isinstance(error, (KeyError, TypeError)):
                failure = ProviderFailure("response_schema_validation", "invalid_response_schema")
            elif returned:
                failure = ProviderFailure("financial_accounting", "accounting_error")
            else:
                failure = ProviderFailure("transport", "operation_call_failed")
            row["state"] = "unknown"
            row["provider_failure"] = failure.diagnostic(row["kind"], round((time.monotonic() - started) * 1000),
                response_received=True if returned else None, http_status=getattr(result, "http_status", None))
            self.save(state)
            raise Stopped("provider_unknown") from None
        row.update(state="settled", cost=cost, **facts)
        elapsed = round((time.monotonic() - started) * 1000)
        if "provider_failure" in facts:
            row["provider_failure"]["elapsed_ms"] = elapsed
        overage = cost > row["reserve"] or facts.get("overage")
        stop = "provider_overage" if overage else facts.get("hold_reason")
        if stop:
            row["state"] = "unknown"
            reason = stop if stop in {"provider_overage", "go_expired", "calibration_finish_not_stop"} else "accounting_hold"
            stage = "response_schema_validation" if reason == "calibration_finish_not_stop" else "financial_accounting"
            row["provider_failure"] = ProviderFailure(stage, reason).diagnostic(
                row["kind"], elapsed, response_received=True, http_status=getattr(result, "http_status", None))
            self.save(state)
            raise Stopped(stop)
        self.save(state)
        return result

    def cancel_unstarted(self, state, keys):
        for key in keys:
            row = state["operations"][key]
            if row["state"] == "reserved":
                row["state"] = "cancelled"
        self.save(state)

    def summary(self, state, run, budget, campaign=None):
        rows = [r for r in state["operations"].values() if r["state"] != "cancelled"
                and (r.get("campaign") == campaign if campaign else r["run"] == run)]
        held = sum(self.accounted(r) for r in rows if r["state"] != "settled")
        settled = sum(r.get("cost", 0) for r in rows if r["state"] == "settled")
        return dict(settled_micro_usd=settled, held_micro_usd=held,
                    remaining_micro_usd=max(0, budget - held - settled),
                    page_attempts=sum(r.get("pages", 0) for r in rows),
                    operations={kind: sum(r["kind"] == kind for r in rows) for kind in sorted(
                        CHAT_MODES | {"upload", "status", "delete"})})
