import json

import pytest

from ds_dc.candidate_fixture import export_receipt, load_candidate
from ds_dc.evidence_lab import demo_matrix
from ds_dc.recovery import Q01_WIRE


def test_synthetic_matrix_uses_independent_expected_outcomes():
    rows = demo_matrix()
    assert len(rows) == 12
    assert all(row["actual"] == row["expected"] for row in rows)
    assert rows[0]["legacy"] == "invalid_locator"
    assert rows[0]["actual"] == "supported_fixture"
    assert all(row["actual"] != "supported_fixture" for row in rows[1:])


def test_export_retains_raw_bytes_and_excludes_receipt_envelope(tmp_path):
    candidate = dict(answer_candidate="draft", status_hint="partial", claims=[], unresolved=[])
    raw = json.dumps(candidate, indent=2) + "\n"
    receipt = dict(candidate=candidate, raw_draft=raw, wire_sha256=Q01_WIRE,
                   finish_reason="stop", account="private-envelope-field")
    path = tmp_path / "q01.json"
    pin = export_receipt(receipt, path)
    assert path.read_bytes() == raw.encode("utf-8")
    assert load_candidate(path, pin) == candidate
    path.write_text(raw + " ")
    with pytest.raises(ValueError, match="fixture_sha_mismatch"):
        load_candidate(path, pin)


@pytest.mark.parametrize("fault", ["unknown_key", "file_handle", "changed_raw", "missing", "redacted"])
def test_export_rejects_unsafe_or_unrecoverable_candidates(tmp_path, fault):
    candidate = dict(answer_candidate="draft", status_hint="partial", claims=[], unresolved=[])
    raw = json.dumps(candidate)
    if fault == "unknown_key":
        candidate["account"] = "private"
    if fault in {"file_handle", "redacted"}:
        candidate["answer_candidate"] = "file-api-private" if fault == "file_handle" else "[redacted credential]"
        raw = json.dumps(candidate)
    if fault == "changed_raw":
        raw = "{}"
    if fault == "missing":
        candidate = None
    path = tmp_path / "rejected.json"
    with pytest.raises(ValueError):
        export_receipt(dict(candidate=candidate, raw_draft=raw, wire_sha256=Q01_WIRE,
                            finish_reason="stop"), path)
    assert not path.exists()


def test_replay_uses_frozen_corpus_without_sending(tmp_path, monkeypatch):
    import os
    from pathlib import Path

    from ds_dc.evidence_lab import replay

    if not all(os.environ.get(key) for key in ("SATURN_SOURCE", "DS_DC_CACHE")):
        pytest.skip("Frozen Saturn fixtures are required")
    from ds_dc.native import NativeD1

    def no_send(*args, **kwargs):
        raise AssertionError("offline replay must not send")

    monkeypatch.setattr(NativeD1, "send", no_send)
    manifest = json.loads(Path("docs/reports/ds-dc-02/corpus-manifest.json").read_text())
    source = manifest["dossiers"]["saturn:device:bkd-pk-rf-2"]["pages"][0]
    claims = [
        dict(claim_id=str(i), scope="Invented display name", component="example",
             literal="synthetic placeholder", value="", unit="", qualifier="", condition="",
             locators=[dict(doc_id=source["id"], sha256=source["sha256"], field_path="line:1",
                            quote="synthetic quote")])
        for i in range(2)
    ]
    fixture = tmp_path / "synthetic.json"
    candidate = dict(answer_candidate="synthetic example", status_hint="candidate", claims=claims, unresolved=[])
    pin = export_receipt(dict(candidate=candidate, wire_sha256=Q01_WIRE, finish_reason="stop"), fixture)
    report = replay(fixture, pin, Path(os.environ["SATURN_SOURCE"]), Path(os.environ["DS_DC_CACHE"]))
    assert report["legacy"] == "invalid_locator"
    assert len(report["claims"]) == 2
    assert all("site_scope_mismatch" in item["checks"] and "site_quote_mismatch" in item["checks"]
               for item in report["claims"])
    assert load_candidate(fixture, pin) == candidate
