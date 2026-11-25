"""Offline evidence inspection. Original ledgers and checkpoints are read-only."""
import argparse
import csv
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from bundle import verify_zip
from protocol import ENDPOINTS, MODEL, STAGES, Stop, load, offline, reply, save, sha

ID = re.compile(r"[A-Za-z][A-Za-z0-9._-]{0,127}\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
SAFE_STAGES = {"connect", "send", "headers", "read", "parse", "usage", "complete",
               "persist_pending", "persist_response", "persist_result", "persist_diagnostic",
               "persist_ledger", "persist_clear_inflight"}
SAFE_EXCEPTIONS = {"HTTPStatusError", "TimeoutError", "ConnectionError", "ConnectionResetError",
                   "ConnectionRefusedError", "RemoteDisconnected", "IncompleteRead", "JSONDecodeError",
                   "UnicodeDecodeError", "ProviderContract", "OSError", "PermissionError", "SSLError",
                   "gaierror", "Stop", "KeyboardInterrupt", "StreamFormat"}


def safe_diagnostic(path):
    if not path.is_file():
        return None
    try:
        row = load(path)
        return dict(
            stage=row["stage"] if row["stage"] in SAFE_STAGES else None,
            exception=row["exception"] if row["exception"] in SAFE_EXCEPTIONS else None,
            response_complete=row.get("response_complete") is True,
            **{field: row[field] for field in ("sse_done", "sse_finish_seen", "sse_usage_seen",
                "sse_events", "sse_keepalives", "sse_content_bytes", "sse_reasoning_bytes")
               if type(row.get(field)) in (int, bool)},
            endpoint=row["endpoint"] if row["endpoint"] in ENDPOINTS else None,
            request_id_available=bool(row.get("request_id")),
            response_id_available=bool(row.get("response_id")),
            **{key: row[key] if type(row.get(key)) is int else None
               for key in ("request_bytes", "response_bytes", "elapsed_ms", "http_status")},
        )
    except (ValueError, TypeError, KeyError, OSError):
        return None


def summarize(path):
    ledger_bytes = path.read_bytes()
    data = json.loads(ledger_bytes)
    seen = set()
    rows = []
    for op in data["ops"]:
        stage, id_, status = (op[key] for key in ("stage", "id", "status"))
        amount, cost = op["reserve_nd"], op.get("cost_nd")
        if (stage not in STAGES or not ID.fullmatch(id_) or (stage, id_) in seen
                or status not in {"SETTLED", "PENDING", "UNKNOWN"}
                or type(amount) is not int or amount <= 0
                or status == "SETTLED" and (type(cost) is not int or not 0 <= cost <= amount)):
            raise Stop("Invalid operation history")
        seen.add((stage, id_))
        root = path.parent
        diag_path = root / "diagnostics" / stage / (id_ + ".json")
        checkpoint = root / stage / (id_ + ".json")
        check, usage = "absent", None
        if checkpoint.is_file():
            check = "unbound_or_mismatch"
            try:
                raw = checkpoint.read_bytes()
                result = json.loads(raw)
                if (isinstance(result, dict) and sha(raw) == op.get("result_sha256")
                        and result.get("cost_nd") == cost and status == "SETTLED"):
                    check = "verified"
                    counts = result.get("usage")
                    keys = ("prompt_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens",
                            "completion_tokens", "reasoning_tokens")
                    if isinstance(counts, dict):
                        usage = {key: counts[key] if type(counts.get(key)) is int else None for key in keys}
            except (OSError, ValueError, RecursionError):
                pass
        diag = safe_diagnostic(diag_path)
        response = root / "responses" / stage / (id_ + ".bin")
        response_check = "absent"
        if response.is_file():
            response_check = ("matches_private_diagnostic" if diag and
                              sha(response.read_bytes()) == load(diag_path).get("response_sha256") else "unbound_or_mismatch")
        rows.append(dict(stage=stage, id=id_, status=status, cost_nd=cost if status == "SETTLED" else None,
                         retained_nd=amount if status != "SETTLED" else 0,
                         checkpoint=check, raw_response=response_check, diagnostic=diag, usage=usage))
    inflight = path.parent / ".inflight"
    unmatched_retained = 0
    if inflight.exists():
        mark = load(inflight)
        matches = [row for row in rows if (row["stage"], row["id"]) == (mark["stage"], mark["id"])]
        if not matches or matches[0]["status"] == "SETTLED":
            unmatched_retained = mark["reserve_nd"]
            if type(unmatched_retained) is not int or unmatched_retained <= 0:
                raise Stop("Invalid durable in-flight marker")
    verified = [row["usage"] for row in rows if row["usage"] is not None]
    usage_totals = {key: dict(quantity=sum(row[key] or 0 for row in verified),
                              unknown=sum(row[key] is None for row in verified))
                    for key in verified[0]} if verified else {}
    return dict(ledger_sha256=sha(ledger_bytes), operations=rows, verified_usage_totals=usage_totals,
                confidence="local_checkpoint_correspondence; no per-operation billing proof",
                spent_nd=sum(row["cost_nd"] or 0 for row in rows),
                retained_nd=sum(row["retained_nd"] for row in rows) + unmatched_retained,
                unmatched_retained_nd=unmatched_retained, inflight=inflight.exists(), blocked=inflight.exists() or any(row["status"] != "SETTLED" or
                         row["checkpoint"] != "verified" for row in rows))


def aggregate_csv(path):
    """Read a locally normalized provider export, dropping account and key fields."""
    aggregates = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"time", "model", "usage_type", "quantity", "cost_usd"} <= set(reader.fieldnames or []):
            raise Stop("CSV needs time,model,usage_type,quantity,cost_usd")
        for row in reader:
            instant = datetime.fromisoformat(row["time"])
            if instant.utcoffset() is None:
                raise Stop("CSV time requires a UTC offset")
            hour = instant.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0).isoformat()
            model = row["model"].lower()
            model = model if model in {MODEL, "deepseek-v4.1-flash-1017", "deepseek-pro"} else "other"
            kind = row["usage_type"]
            if kind not in {"prompt_hit", "prompt_miss", "completion", "reasoning", "ocr", "request"}:
                raise Stop("Unsupported normalized CSV usage type")
            quantity = int(row["quantity"])
            cost = Decimal(row["cost_usd"]) * 10**9
            if quantity < 0 or not cost.is_finite() or cost < 0 or cost != cost.to_integral_value():
                raise Stop("Invalid CSV amount")
            entry = aggregates.setdefault((hour, model, kind), [0, 0])
            entry[0] += quantity
            entry[1] += int(cost)
    return [dict(hour=hour, model=model, usage_type=kind, quantity=q, cost_nd=c)
            for (hour, model, kind), (q, c) in sorted(aggregates.items())]


def independent_proof(ledger, summary, approval, evidence):
    """Write a reviewable reconstruction based on separately verified evidence."""
    if (set(approval) != {"operation", "stage", "owner_go", "disposition", "evidence_sha256"}
            or not isinstance(approval["owner_go"], str) or not approval["owner_go"].strip()
            or approval["evidence_sha256"] != sha(evidence.read_bytes())
            or evidence.resolve().is_relative_to(ledger.parent.resolve())):
        raise Stop("Require separate evidence with matching digest and explicit Owner GO")
    op = next((op for op in load(ledger)["ops"]
               if (op["stage"], op["id"]) == (approval["stage"], approval["operation"])), None)
    if not op or op["status"] not in {"UNKNOWN", "PENDING"}:
        raise Stop("Independent decision must bind a blocking operation")
    proof = load(evidence)
    if not isinstance(proof, dict) or proof.get("request_sha256") != op["request_sha256"]:
        raise Stop("Independent evidence lacks exact request linkage")
    output = dict(approval=approval, ledger_sha256=summary["ledger_sha256"],
                  request_sha256=op["request_sha256"])
    if approval["disposition"] == "verified_response":
        path = ledger.parent / "responses" / op["stage"] / (op["id"] + ".bin")
        raw = path.read_bytes()
        if sha(raw) != proof.get("response_sha256"):
            raise Stop("Independently verified response hash differs")
        if op.get("parameters", {}).get("stream") is True:
            from sse import ChatStream

            stream = ChatStream()
            stream.feed(raw)
            raw_object = stream.assembled()
        else:
            raw_object = json.loads(raw)
        if op.get("endpoint") == "/files":
            from compile_d import uploaded
            from protocol import PAGE

            original_pages, remainder = divmod(op["reserve_nd"], PAGE)
            if remainder or proof.get("expected_pages") != original_pages or type(proof.get("expected_bytes")) is not int:
                raise Stop("Upload proof requires the original page and byte counts")
            result = uploaded(raw_object, proof["expected_bytes"], original_pages)
        else:
            result = reply(raw_object, op["parameters"]["max_tokens"])
        if result["cost_nd"] > op["reserve_nd"]:
            raise Stop("Reconstructed cost exceeds original reserve")
        output["reconstructed_result"] = result
    elif approval["disposition"] == "provider_confirmed_no_charge":
        if proof.get("disposition") != approval["disposition"]:
            raise Stop("No-charge disposition requires a separate exact provider decision")
        output["provider_disposition"] = approval["disposition"]
    else:
        raise Stop("Unsupported independent disposition")
    return output


def reviewed_links(index, identity, attestation):
    """Record explicit engineering links while preserving the original knowledge rows."""
    if attestation["knowledge_identity"] != identity or not attestation["reviewer"].strip():
        raise Stop("Engineering link attestation must bind this knowledge identity")
    facts = {row["fact_id"]: row for row in index}
    linked = set()
    for link in attestation["links"]:
        left, right = link["unresolved"], link["assertion"]
        if (facts[left]["kind"] != "unresolved" or facts[right]["kind"] != "source_assertion"
                or not link["applicability_verified"] is True or not link["evidence"].strip()):
            raise Stop("A reviewed link must tie an unresolved record to a supported assertion and its applicability")
        linked.add((left, right))
    return [dict(unresolved=left, assertion=right, status="engineer_attested")
            for left, right in sorted(linked)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--knowledge-zip", type=Path)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--verified-links", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--independent-evidence", type=Path)
    args = parser.parse_args()
    offline()
    if args.output.exists() or args.output.resolve().is_relative_to(args.ledger.parent.resolve()):
        raise Stop("Choose a fresh output outside the original state")
    result = summarize(args.ledger)
    if args.verified_links and not args.knowledge_zip:
        raise Stop("A reviewed link file requires its verified knowledge ZIP")
    if args.knowledge_zip:
        meta = verify_zip(args.knowledge_zip)
        result["knowledge"] = {key: meta[key] for key in ("status", "identity", "snapshot")}
        import zipfile
        with zipfile.ZipFile(args.knowledge_zip) as bundle:
            coverage = json.loads(bundle.read("coverage.json"))
            index = json.loads(bundle.read("index.json"))
            result["knowledge"].update(fact_count=len(index), task_count=len(coverage["tasks"]),
                                       documents=len(coverage["sources"]))
        if args.verified_links:
            raw = args.verified_links.read_bytes()
            result["knowledge"]["attestation_sha256"] = sha(raw)
            result["knowledge"]["reviewed_links"] = reviewed_links(index, meta["identity"], json.loads(raw))
    if args.csv:
        result["aggregate_csv"] = aggregate_csv(args.csv)
        result["csv_confidence"] = "Aggregate corroboration only; exact operation outcome unproven"
    if bool(args.approval) != bool(args.independent_evidence):
        raise Stop("Specify both an approval and independent evidence")
    if args.approval:
        result["private_reconstruction"] = independent_proof(
            args.ledger, result, load(args.approval), args.independent_evidence)
    save(args.output, result)


if __name__ == "__main__":
    try:
        main()
    except (Stop, OSError, ValueError, TypeError, KeyError, InvalidOperation) as error:
        raise SystemExit(str(error) if isinstance(error, Stop) else type(error).__name__) from None
