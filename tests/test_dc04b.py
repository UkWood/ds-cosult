"""Admission and native accounting for the one recorded experiment."""
from copy import deepcopy
import hashlib
import json

import pytest

from ds_dc import quality_lab as lab, recovery
from ds_dc.finance import Ledger, OWNER, Stopped

NOW = 1795383600
HEAD = "a" * 40
KEY = "credential-for-dc04b-test"
ACCOUNT = "test-account"
PROJECT = "test-project"


@pytest.fixture
def history(tmp_path):
    ledger = Ledger(tmp_path / "ledger")
    labels = dict(account=ACCOUNT, project=PROJECT, key_sha256=hashlib.sha256(KEY.encode()).hexdigest())
    original_permit = labels | dict(run="q01-original", kind="controlled_calibration",
        cal_id="Q01", head=recovery.ORIGINAL_HEAD, manifest_sha=recovery.MANIFEST,
        wire_sha256=recovery.Q01_WIRE, accepted_residual_risk=True)
    original_sha = recovery.fingerprint(original_permit)
    prior = dict(run=original_permit["run"], campaign=recovery.CAMPAIGN, profile="owner")
    rows = {recovery.ORIGINAL_CHAT: prior | dict(
        kind="calibration", slot="extended", state="cancelled", reserve=330_000,
        permit_sha=original_sha, calibration_scope=recovery.scope(labels, recovery.ORIGINAL_HEAD))}
    for key, pages in recovery.ORIGINAL_UPLOADS.items():
        rows[key] = prior | dict(kind="upload", pages=pages, reserve=pages * 225,
                                state="unknown" if key == recovery.ORIGINAL_UPLOAD else "cancelled")
    state = dict(operations=rows, runs={prior["run"]: original_sha}, bindings={})
    archive = json.dumps(state).encode()
    recovery_head = "b" * 40
    auth = recovery.authorization_payload(state, archive, original_permit, recovery_head, "owner")
    auth_sha = recovery.fingerprint(auth)
    archive_path = tmp_path / "incident-archive"
    archive_path.mkdir(mode=0o700)
    for path, raw in ((archive_path / "ledger.json", archive),
                      (archive_path / "go-Q01.json", json.dumps(original_permit).encode()),
                      (tmp_path / "CAL-INC-01-authorization.json", json.dumps(auth).encode())):
        path.write_bytes(raw)
        path.chmod(0o400)
    recovered_go = original_permit | dict(run="q01-recovery", head=recovery_head,
                                         recovery_authorization_sha=auth_sha)
    recovered_sha = recovery.fingerprint(recovered_go)
    (tmp_path / "go-Q01-recovery.json").write_text(json.dumps(recovered_go))
    (tmp_path / "go-Q01-recovery.json").chmod(0o400)
    state["recovery_events"] = [
        dict(kind="authorized", authorization_sha=auth_sha, authorization=auth),
        dict(kind="consumed", authorization_sha=auth_sha, operation=recovery.RECOVERY_CHAT,
             permit_sha=recovered_sha),
    ]
    state["operations"][recovery.RECOVERY_CHAT] = prior | dict(
        run="q01-recovery", kind="calibration", slot="extended", state="settled",
        reserve=330_000, cost=18_600, permit_sha=recovered_sha, calibration_scope=auth["account_scope"],
    )
    for original_key, pages in recovery.ORIGINAL_UPLOADS.items():
        key = recovery.RECOVERY_CHAT + "/upload/" + original_key.rsplit("/", 1)[-1]
        state["operations"][key] = prior | dict(
            run="q01-recovery", kind="upload", pages=pages, reserve=225 * pages,
            state="settled", cost=225 * pages)
    state["runs"]["q01-recovery"] = recovered_sha
    state["bindings"]["old"] = dict(account=ACCOUNT, project=PROJECT, id="file-api-historical")
    ledger.save(state)
    with ledger.transaction(maintain=False):
        pass
    return ledger


def test_exact_incident_reservation_is_atomic_and_single_use(history):
    from ds_dc import dc04b_permit as permit

    with history.transaction(maintain=False) as state:
        before = deepcopy(state)
        basis = permit.admit(state)
        approval = permit.issue(state, basis, HEAD, KEY, NOW)
        permit.reserve(history, state, approval, NOW)
        assert state["recovery_events"] == before["recovery_events"]
        assert all(state["operations"][key] == row for key, row in before["operations"].items())
        added = [row for key, row in state["operations"].items() if key not in before["operations"]]
        assert len(added) == 5 and sum(row["reserve"] for row in added) == 500_000
        assert sum(row.get("pages", 0) for row in added) == 80
        assert [row["reserve"] for row in added if row["kind"] == "calibration"] == [482_000]
        assert state["dc04b_events"][0]["permit"] == approval
        assert json.loads(history.file.read_bytes()) == state
        with pytest.raises(Stopped, match="dc04b_already_reserved"):
            permit.admit(state)
        with pytest.raises(Stopped, match="provider_unknown"):
            history.reserve(state, "ordinary", "permit", "owner", NOW, OWNER,
                            {"ordinary": dict(kind="extended", reserve=1)}, campaign=recovery.CAMPAIGN)


@pytest.mark.parametrize("change", ["historical_reserve", "original_missing", "original_state",
    "history_digest", "history_consumption", "unrelated_unknown", "unrelated_inflight", "budget", "pages",
    "uploads", "chats", "extended", "calibration", "ledger_changed", "key", "approval", "contract",
    "head", "wire", "expiry", "operation", "missing_ledger"])
def test_rejects_changes_before_reservation(history, change, monkeypatch):
    from ds_dc import dc04b_permit as permit

    if change == "missing_ledger":
        history.file.unlink()
        with pytest.raises(Stopped, match="ledger_path_invalid"):
            permit.open_ledger(history.path)
        return
    with history.transaction(maintain=False) as state:
        basis = permit.admit(state)
        if change == "key":
            with pytest.raises(Stopped, match="account_scope_mismatch"):
                permit.issue(state, basis, HEAD, "unrecognized", NOW)
            return
        if change == "approval":
            monkeypatch.setattr(permit, "OWNER_APPROVAL", None)
            with pytest.raises(Stopped, match="financial_authorization_missing"):
                permit.issue(state, basis, HEAD, KEY, NOW)
            return
        if change in {"contract", "head", "wire", "expiry", "operation"}:
            approval = permit.issue(state, basis, HEAD, KEY, NOW)
            field = {"contract": "contract_digest", "head": "head", "wire": "wire",
                     "expiry": "expires", "operation": "operations"}[change]
            approval[field] = None
            with pytest.raises(Stopped, match="permit_mismatch"):
                permit.reserve(history, state, approval, NOW)
            return
        if change == "original_missing":
            del state["operations"][recovery.ORIGINAL_UPLOAD]
        elif change == "original_state":
            state["operations"][recovery.ORIGINAL_UPLOAD].update(state="settled", cost=14625)
        elif change == "historical_reserve":
            state["operations"][recovery.ORIGINAL_UPLOAD]["reserve"] += 1
        elif change == "history_digest":
            state["recovery_events"][0]["authorization"]["original_operations_sha"] = "a" * 64
        elif change == "history_consumption":
            state["recovery_events"][1]["permit_sha"] = "e" * 64
        elif change == "ledger_changed":
            state["bindings"]["new"] = dict(account=ACCOUNT, project=PROJECT)
        else:
            rows = {
                "unrelated_unknown": [{}], "unrelated_inflight": [{}],
                "budget": [dict(cost=1_800_000)], "pages": [dict(pages=856)],
                "uploads": [dict(kind="upload")] * 25, "chats": [dict(kind="normal")] * 24
                    + [dict(kind="extended")] * 7,
                "extended": [dict(kind="extended")] * 8, "calibration": [dict(kind="calibration")],
            }[change]
            status = change.removeprefix("unrelated_") if change.startswith("unrelated_") else "settled"
            for number, extras in enumerate(rows):
                state["operations"][f"extra-{number}"] = dict(
                    run="other", profile="owner", campaign=recovery.CAMPAIGN, kind="upload",
                    state=status, cost=0, reserve=0) | extras
        with pytest.raises(Stopped):
            permit.issue(state, basis, HEAD, KEY, NOW)
        assert "dc04b_events" not in json.loads(history.file.read_bytes())


from test_dc04a import experiment, fake_boundary
from test_dc03c import synthetic_corpus


@pytest.fixture
def pinned_experiment(monkeypatch, experiment):
    from ds_dc import dc04b_permit as permit

    plan, cache = experiment
    monkeypatch.setattr(permit, "FILES", tuple((sha, pages, (cache / f"{sha}.pdf").stat().st_size)
                                              for sha, pages in plan.files))
    monkeypatch.setattr(permit, "MANIFEST", plan.manifest)
    monkeypatch.setattr(permit, "WIRE", plan.wire)
    monkeypatch.setattr(permit, "PAYLOAD", plan.payload_digest)
    monkeypatch.setattr(permit, "REGISTRY", plan.registry.wire_identity)
    monkeypatch.setattr(lab, "git_head", lambda: plan.commit)
    return plan


@pytest.mark.parametrize(("mode", "calls", "chat_state", "known", "candidate_status"), [
    ("ok", 5, "settled", 18319, "reference"),
    ("invalid", 5, "settled", 18319, "invalid_contract"),
    ("incomplete", 5, "settled", 18319, "incomplete"),
    ("unknown", 5, "unknown", 18000, "reference"),
    ("timeout", 5, "unknown", 18000, "unavailable"),
    ("upload_rejected", 2, "cancelled", 4500, "unavailable"),
    ("chat_rejected", 5, "unknown", 18000, "unavailable"),
    ("malformed_envelope", 5, "unknown", 18000, "unavailable"),
    ("duplicate_usage", 5, "unknown", 18000, "unavailable"),
    ("redirect", 5, "unknown", 18000, "unavailable"),
    ("response_percent", 5, "settled", 18319, "reference"),
    ("response_secret", 5, "settled", 18319, "needs_support"),
    ("response_encoded_secret", 5, "settled", 18319, "needs_support"),
])
def test_native_experiment_and_replay(history, pinned_experiment, experiment, synthetic_corpus,
                                      mode, calls, chat_state, known, candidate_status):
    import httpx
    from ds_dc import dc04b, dc04b_permit as permit

    entries, dossiers, cache = synthetic_corpus
    inner, requests = fake_boundary(experiment, mode)

    def boundary(request):
        assert request.headers["Authorization"] == f"Bearer {KEY}"
        with history.file.open() as file:
            state = json.load(file)
        assert len(state["dc04b_events"]) == 1
        assert set(permit.operations()) <= state["operations"].keys()
        response = inner.handle_request(request)
        if request.url.path == "/files" and response.is_success:
            data = response.json()
            data.update(created_at=NOW, expires_at=NOW + 3600)
            return httpx.Response(200, json=data)
        if len(requests) == 5:
            if mode == "chat_rejected":
                return httpx.Response(502, content=b"broken")
            if mode == "malformed_envelope":
                return httpx.Response(200, content=b"{")
            if mode == "duplicate_usage":
                return httpx.Response(200, content=response.content[:-1] + b', "usage": {}}')
            if mode == "redirect":
                return httpx.Response(307, headers={"Location": "https://api.deepseek.com/chat/completions"},
                                      content=response.content)
            if mode == "response_percent":
                return httpx.Response(200, json=response.json() | {"diagnostic": "99% coverage"})
            if mode in {"response_secret", "response_encoded_secret"}:
                data = response.json()
                candidate = json.loads(data["choices"][0]["message"]["content"])
                candidate["evidence_extracts"][0]["quote"] += " " + KEY
                data["choices"][0]["message"]["content"] = json.dumps(candidate)
                if mode == "response_encoded_secret":
                    encoded_key = b"".join(f"\\u{ord(char):04x}".encode() for char in KEY)
                    return httpx.Response(200, content=json.dumps(data).encode().replace(KEY.encode(), encoded_key))
                return httpx.Response(200, json=data)
        return response

    with history.transaction(maintain=False) as state:
        basis = permit.admit(state)
    with httpx.MockTransport(boundary) as transport:
        report = dc04b.run_experiment(entries, dossiers, cache, pinned_experiment, history, basis,
                                     key_reader=lambda: KEY, transport=transport, clock=lambda: NOW)
    assert len(requests) == calls and [route for route, _ in requests] == (
        ["/files"] * min(calls, 4) + ["/chat/completions"] * (calls == 5))
    assert report["candidate_status"] == candidate_status
    assert report["telemetry"]["cost_micro_usd"]["known"] == known
    assert report["financial"]["chat_state"] == chat_state
    assert report["financial"]["campaign_remaining_micro_usd"] > 0
    assert report["expert_score"] == "NOT RUN"
    if mode == "ok":
        assert report["A"]["evidence_extracts"][0]["quote"] == "Устройство хранит записи локально."
        assert report["B"]["answer"]
        assert report["provenance"]["actual_payload_sha256"] == hashlib.sha256(requests[-1][1]).hexdigest()
        assert report["telemetry"]["tokens"]["reasoning"] == 10
        assert report["observed_model_alias"] == "deepseek-flash" and report["finish_reason"] == "stop"
    raw = dc04b.private_directory(history) / "native-response.bin"
    if mode in {"response_secret", "response_encoded_secret"}:
        assert report["response_capture"] == "credential_detected"
        assert not raw.exists()
    elif calls == 5 and mode != "timeout":
        assert raw.exists() and not raw.stat().st_mode & 0o077
    exported = json.dumps(report, ensure_ascii=False)
    for private in (KEY, "file-api-", "private-mock-reasoning", str(history.path)):
        assert private not in exported
    assert KEY.encode() not in history.file.read_bytes()
    assert all(KEY.encode() not in path.read_bytes() for path in raw.parent.iterdir())
    assert dc04b.replay_report(history) == report
    if mode == "ok":
        with history.transaction(maintain=False) as state:
            state["dc04b_events"].pop()
            history.save(state)
        assert dc04b.replay_report(history) == report
    assert len(requests) == calls


def test_preflight_and_ledger_changes_stop_before_credential(history, pinned_experiment, synthetic_corpus,
                                                            monkeypatch):
    from dataclasses import replace
    import httpx
    from ds_dc import dc04b, dc04b_permit as permit

    def forbidden(*_):
        pytest.fail("The failed admission tried to read the key or send HTTP")

    entries, dossiers, cache = synthetic_corpus
    with history.transaction(maintain=False) as state:
        basis = permit.admit(state)
    with httpx.MockTransport(forbidden) as transport:
        for field, reason in (("commit", "head_mismatch"), ("wire", "wire_drift")):
            revised = replace(pinned_experiment, **{field: "f" * (40 if field == "commit" else 64)})
            with pytest.raises(Stopped, match=reason):
                dc04b.run_experiment(entries, dossiers, cache, revised, history, basis,
                                     key_reader=forbidden, transport=transport, clock=lambda: NOW)
        monkeypatch.setattr(permit, "CONTRACT_DIGEST", "f" * 64)
        with pytest.raises(Stopped, match="contract_unreviewed"):
            dc04b.run_experiment(entries, dossiers, cache, pinned_experiment, history, basis,
                                 key_reader=forbidden, transport=transport, clock=lambda: NOW)
    assert not dc04b.replay_report(history)


def test_launcher_bootstrap_failure_exports_one_safe_zip(tmp_path):
    import subprocess
    import sys
    import zipfile
    from pathlib import Path

    launcher = Path(__file__).resolve().parents[1] / "scripts/validation/validate_dc04b.py"
    output = tmp_path / "reports"
    process = subprocess.run([sys.executable, "-I", str(launcher), "--commit", "bad",
                              "--blob", "b" * 40, "--output", str(output)],
                             input="", text=True, capture_output=True, timeout=20)
    assert process.returncode == 1
    assert "DeepSeek API KEY" not in process.stdout + process.stderr
    archive, = output.glob("*.zip")
    with zipfile.ZipFile(archive) as report:
        assert report.testzip() is None
        assert report.namelist() == ["summary.json", "SHA256SUMS"]
        summary = json.loads(report.read("summary.json"))
        assert summary["status"] == "invalid_launch_pin"
        assert summary["live"] == "LIVE_NOT_RUN"
        assert summary["new_provider_operations"] == 0
        assert str(tmp_path) not in report.read("summary.json").decode()


@pytest.mark.parametrize("rewrite", ["authorization", "consumption", "recovered_upload"])
def test_original_archive_pins_history_against_ledger_rewrite(history, rewrite):
    from ds_dc import dc04b_permit as permit

    with history.transaction(maintain=False) as state:
        archive = history.path.parent / "incident-archive"
        assert permit.confirm_archive(state, archive) == (ACCOUNT, PROJECT)
        if rewrite == "authorization":
            auth = state["recovery_events"][0]["authorization"]
            auth["owner"] = "rewritten-owner"
            for event in state["recovery_events"]:
                event["authorization_sha"] = recovery.fingerprint(auth)
        elif rewrite == "consumption":
            state["operations"][recovery.RECOVERY_CHAT]["permit_sha"] = "e" * 64
            state["recovery_events"][1]["permit_sha"] = "e" * 64
            state["runs"]["q01-recovery"] = "e" * 64
        else:
            key = recovery.RECOVERY_CHAT + "/upload/" + recovery.ORIGINAL_UPLOAD.rsplit("/", 1)[-1]
            state["operations"][key]["pages"] -= 1
        with pytest.raises(Stopped, match="incident_archive_mismatch"):
            permit.confirm_archive(state, archive)


def test_bare_live_stage_cannot_accept_caller_supplied_pass_files(history, tmp_path):
    import subprocess
    import sys

    # Only the offline worker and replay are exposed by this module's CLI.
    process = subprocess.run([sys.executable, "-m", "ds_dc.quality_lab", "live", "--stage", "execute",
                              "--ledger", str(history.path), "--receipt", str(tmp_path / "receipt.json")],
                             text=True, capture_output=True, timeout=20)
    assert process.returncode == 2
    assert "invalid choice" in process.stderr
    assert "DeepSeek API KEY" not in process.stdout + process.stderr


def test_failed_wsl_acceptance_cannot_start_live_coordinator(history, tmp_path, monkeypatch):
    from types import SimpleNamespace

    from ds_dc import dc04b, dc04b_permit
    from scripts.validation import validate_dc04b as launcher

    def offline_fail(*_):
        raise ValueError("offline_acceptance_failed")

    def forbidden(*_):
        pytest.fail("The coordinator entered live code after failed isolation")

    monkeypatch.setattr(launcher.os, "uname", lambda: SimpleNamespace(release="microsoft-WSL2"))
    monkeypatch.setattr(launcher, "check_checkout", lambda *_: None)
    monkeypatch.setattr(launcher, "isolated_acceptance", offline_fail)
    monkeypatch.setattr(dc04b_permit, "canonical_ledger", lambda: history.path)
    monkeypatch.setattr(dc04b, "execute_prepared", forbidden)
    checkout = tmp_path / "checkout"
    monkeypatch.syspath_prepend(str(checkout))
    with pytest.raises(ValueError, match="offline_acceptance_failed"):
        launcher.coordinate(SimpleNamespace(), checkout, tmp_path)
    assert not (tmp_path / "execution-started").exists()
    assert not dc04b.replay_report(history)
