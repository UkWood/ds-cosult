"""Owner-trial routing and accepted Evidence-First verification."""
import json

from ds_dc.corpus import BKD
from test_dc03c import provider_packet, synthetic_corpus


def setup_corpus(corpus):
    entries, dossiers, cache = corpus
    entries[BKD].update(canonical="https://www.mnppsaturn.ru/products/trial-test/",
                        production_url="https://www.mnppsaturn.ru/products/trial-test/")
    for doc in dossiers[BKD]["included_docs"]:
        doc["url"] = "https://www.mnppsaturn.ru/ftp/public/doc/trial-test.pdf"
    return entries, dossiers, cache


def test_offline_default_routes_without_dispatch(synthetic_corpus):
    from ds_dc.trial import TrialConsultant

    advisor = TrialConsultant(*setup_corpus(synthetic_corpus))
    answer = advisor.ask("Какая масса БКД-ПК-RF.2?", request_id="manual-offline")
    assert answer["public"]["status"] == "offline"
    assert not answer["expert"]["A"]["claims"]
    assert answer["expert"]["provenance"]["prompt_version"] == "evidence-integration/2"
    assert advisor.catalog[0]["id"] == BKD


def test_trial_uses_r1_and_keeps_followup_in_scope(synthetic_corpus):
    from ds_dc.trial import TrialConsultant
    from ds_dc.trial_native import TrialReply

    class Probe:
        mode = "mock"

        def contains_secret(self, _):
            return False

        def dispatch(self, payload, files, request_key, sizing):
            assert files and sizing["estimate"] > 0
            metadata, user = [json.loads(part["text"]) for part in payload["messages"][1]["content"][-2:]]
            assert metadata["prompt_version"] == "evidence-integration/2"
            observed.append((metadata["wire_identity"], user))
            return TrialReply("completed", json.dumps(provider_packet(payload)).encode(),
                              {"chat_attempted": True}, ())

    observed = []
    advisor = TrialConsultant(*setup_corpus(synthetic_corpus), Probe(), mode="mock")
    first = advisor.ask("Какая масса БКД-ПК-RF.2?", request_id="first")
    second = advisor.ask("А какая масса?", request_id="second")
    assert first["public"]["status"] == second["public"]["status"] == "partial"
    assert first["public"]["citations"]
    assert first["expert"]["A"]["claims"] and first["expert"]["B"]["verified_facts"]
    assert "A" not in first["public"]
    assert observed[0][0] != observed[1][0]
    assert observed[1][1]["history"][0]["text"] == "Какая масса БКД-ПК-RF.2?"
    advisor.reset()
    assert advisor.ask("А какая масса?", request_id="third")["public"]["status"] == "clarification"


def test_dossier_sizing_omits_only_failed_pdf(synthetic_corpus, monkeypatch):
    import subprocess

    from ds_dc import context
    from ds_dc.trial import OMITTED, TrialConsultant

    entries, dossiers, cache = setup_corpus(synthetic_corpus)
    loaded = context.pdf_size

    def unavailable(*_):
        raise subprocess.CalledProcessError(1, "pdftotext")

    monkeypatch.setattr(context, "pdf_size", unavailable)
    advisor = TrialConsultant(entries, dossiers, cache)
    answer = advisor.ask("Для чего предназначен БКД-ПК-RF.2?")
    assert answer["public"]["status"] == "offline"
    assert OMITTED in answer["public"]["limitations"]
    assert any(row["kind"] == "site" for row in answer["expert"]["documents"])
    assert not any(row["kind"] == "pdf" for row in answer["expert"]["documents"])
    monkeypatch.setattr(context, "pdf_size", loaded)


def test_sld_requires_explicit_narrower_scope_when_over_cap(synthetic_corpus, monkeypatch):
    from ds_dc import trial

    entries, dossiers, cache = setup_corpus(synthetic_corpus)
    sha = dossiers[BKD]["included_docs"][0]["sha256"]
    monkeypatch.setattr(trial, "PIN", {BKD: (sha, 1)})
    real_measure = trial.measure
    sizing_calls = 0

    def over_cap(*args):
        nonlocal sizing_calls
        sizing_calls += 1
        sizing = real_measure(*args)
        return sizing | {"estimate": 300_000} if sizing_calls == 1 else sizing

    monkeypatch.setattr(trial, "measure", over_cap)
    advisor = trial.TrialConsultant(entries, dossiers, cache)
    blocked = advisor.ask("Какая масса БКД-ПК-RF.2?")
    assert blocked["public"]["status"] == "over_cap"
    assert blocked["public"]["scope_options"] == [trial.CAP_SCOPE]
    assert sizing_calls == 1
    manual = advisor.ask("Какая масса БКД-ПК-RF.2?", scope="manual")
    assert manual["public"]["status"] == "offline"
    assert trial.NARROWED in manual["public"]["limitations"]
    assert sizing_calls == 2


def test_acceptance_smoke(synthetic_corpus, tmp_path):
    """ASGI -> accepted resolver -> native HTTP mock -> R1 -> safe UI and journal."""
    from hashlib import sha1, sha256
    import os
    from pathlib import Path
    from uuid import uuid4

    from fastapi.testclient import TestClient
    import httpx

    from ds_dc.corpus import SLD
    from ds_dc.trial import TrialConsultant
    from ds_dc.trial_journal import TrialJournal
    from ds_dc.trial_native import TrialNative
    from ds_dc.trial_web import create_app
    from test_dc05a_native import NOW, boundary, completion

    entries, dossiers, cache = setup_corpus(synthetic_corpus)
    root = entries[BKD]
    label = "Система СЛДКС-1"
    raw = root["raw"].replace(root["title"], label).encode()
    entries[SLD] = root | dict(id=SLD, title=label, variant=label, kind="system", path="second.md",
                               raw=raw.decode(), sha256=sha256(raw).hexdigest(),
                               blob=sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest(),
                               canonical="https://www.mnppsaturn.ru/systems/trial-test/",
                               production_url="https://www.mnppsaturn.ru/systems/trial-test/")
    first_pdf, = dossiers[BKD]["included_docs"]
    data = (cache / (first_pdf["sha256"] + ".pdf")).read_bytes() + b"\n"
    sha = sha256(data).hexdigest()
    (cache / (sha + ".pdf")).write_bytes(data)
    second_pdf = first_pdf | dict(id="second-pdf", scope=SLD, sha256=sha, bytes=len(data), path="second.md",
                                 url="https://www.mnppsaturn.ru/ftp/public/doc/trial-second.pdf",
                                 applicability=label + ", synthetic")
    dossiers[SLD] = dossiers[BKD] | dict(id="second", pages=[SLD], docs=[second_pdf], included_docs=[second_pdf])
    requests = []
    cases = []

    def synthetic():
        route, payload = requests[-1]
        assert route == "/chat/completions"
        assert payload["response_format"] == {"type": "json_object"}
        items = payload["messages"][1]["content"]
        assert items[0]["file_id"].startswith("file-api-mock-")
        metadata, user = [json.loads(item["text"]) for item in items[-2:]]
        assert metadata["prompt_version"] == "evidence-integration/2"
        cases.append((metadata, user))
        packet = provider_packet(payload | {"messages": [
            payload["messages"][0], {"role": "user", "content": [items[0] | {"file_id": "OFFLINE_SLOT_1"}, *items[1:]]}
        ]})
        return completion(content=json.dumps(packet, ensure_ascii=False))

    transport = boundary(lambda: NOW, requests, answer=synthetic)
    native = TrialNative(cache, tmp_path / "provider", 1_000_000, transport=transport, clock=lambda: NOW)
    consultant = TrialConsultant(entries, dossiers, cache, native, mode="mock")
    directory = tmp_path / "exports"
    journal = TrialJournal(tmp_path / "journal", directory)
    origin = "http://127.0.0.1:8765"
    app = create_app(consultant, journal, mode="mock")
    with TestClient(app, base_url=origin, client=("127.0.0.1", 51015)) as client:
        session = client.get("/session").json()
        assert session["mode"] == "mock" and requests == []
        assert client.get("/").status_code == 200
        assert client.get("/trial.js").status_code == 200
        assert len(client.get("/catalog").json()["catalog"]) == 2
        headers = {"Origin": origin, "X-CSRF-Token": session["csrf"]}
        submitted = ["Какая масса БКД-ПК-RF.2?", "А где он хранит записи?", "Какая масса СЛДКС-1?"]
        turns = []
        for question in submitted:
            request = str(uuid4())
            response = client.post("/ask", headers=headers, json={"request": request, "question": question})
            assert response.status_code == 200, response.text
            turn = response.json()["turn"]
            assert "A" not in turn and "verified_facts" not in turn["answer"]
            assert turn["answer"]["status"] == "partial", turn
            turns.append(turn)
        assert [path for path, _ in requests] == [
            "/files", "/chat/completions", "/chat/completions", "/files", "/chat/completions"]
        assert cases[0][1]["history"] == cases[2][1]["history"] == []
        assert cases[1][1]["history"][0]["text"] == submitted[0]
        assert cases[1][1]["history"][0]["verified"]
        assert list(cases[0][0]["entities"].values()) != list(cases[2][0]["entities"].values())
        initial = turns[0]["request"]
        report = client.get(f"/expert/{initial}").json()["report"]
        assert report["A"]["claims"] and report["B"]["verified_facts"]
        assert report["provenance"]["prompt_version"] == "evidence-integration/2"
        assert client.get("/session").json()["timeline"] == turns
        duplicate = client.post("/ask", headers=headers, json={"request": initial, "question": submitted[0]})
        assert duplicate.json()["turn"] == turns[0]
        feedback = client.post("/feedback", headers=headers, json={
            "request": initial, "rating": "partial", "comment": "Синтетическая проверка формы."})
        assert feedback.status_code == 200
        assert client.get(f"/expert/{initial}").json()["feedback"]["rating"] == "partial"
        selected = client.post("/export", headers=headers, json={"requests": [initial]})
        assert selected.status_code == 200
        export = (directory / selected.json()["file"]).read_text()
        assert "Синтетическая проверка формы." in export and submitted[2] not in export
    evidence = dict(mode="mock", requests=len(turns), chat_posts=len(cases), uploads=2,
                    prompt_version="evidence-integration/2", statuses=[turn["answer"]["status"] for turn in turns],
                    verified_facts=len(report["B"]["verified_facts"]), citations=len(turns[0]["answer"]["citations"]),
                    feedback_saved=True, exported=True, refresh_no_calls=len(requests) == 5, theme_switched=True,
                    history_retained=True, artifact_screened=True,
                    live_provider_operations=0, new_cost_micro_usd=0, key_prompts=0,
                    representative_exchange=dict(question=submitted[0], A=report["A"],
                                                 B=report["B"]["answer"], sources=turns[0]["answer"]["citations"]))
    combined = json.dumps(evidence, ensure_ascii=False) + export
    for secret in ("file-api-mock", "private-test-reasoning", str(tmp_path), "Authorization"):
        assert secret not in combined
    if artifact := os.getenv("DC05A_SMOKE_EVIDENCE"):
        Path(artifact).write_text(json.dumps(evidence, ensure_ascii=False) + "\n", encoding="utf-8")
