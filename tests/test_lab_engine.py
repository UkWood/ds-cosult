"""Exercise the real admission boundary with an offline recording provider."""
import os
from pathlib import Path

from ds_pilot.catalog import Catalog, load_git
from ds_pilot.engine import Pilot


class Recorder:
    def __init__(self):
        self.reserved = set()
        self.sent = []

    def reserve(self, request):
        if request in self.reserved:
            raise ValueError("duplicate")
        self.reserved.add(request)

    def dispatch(self, request, mode, payload):
        self.sent.append(request)
        if mode == "P1":
            return {"interpretation_status": "supported", "need_ids": ["n1"]}
        return {"question_needs_hash": payload["question_needs_hash"], "selection": payload["candidates"]}

    def receipt(self, request):
        return {"dispatched": request in self.sent}


def test_lab_quota_context_replay_reset_and_paid_fence(tmp_path):
    catalog = Catalog(load_git(Path(os.environ["SATURN_SOURCE"])))
    provider = Recorder()
    pilot = Pilot(catalog, tmp_path / "lab.sqlite", lab=True, live=provider)
    question = "Какая масса БКД-ПК-RF.2?"
    for i in range(26):
        assert pilot.ask(question, "first", str(i), now=1000+i)["status"] == "answered"
    pilot.ask("Что такое СЛДКС-1?", "second", "other", now=1030)
    assert pilot.ask("А его масса?", "first", "follow", now=1031)["status"] == "answered"
    mixed = "Укажи питание БКД-ПК-RF.2 и назначение СЛДКС-1"
    for mode in ["P1", "P2"]:
        response = pilot.ask(mixed, "first", mode, mode=mode, now=1032)
        assert response["status"] == "answered" and len(response["question_needs"]) == 2
        assert pilot.ask(mixed, "first", mode, mode=mode, now=1033) == response
    pilot.reset("first")
    assert not pilot.history("first") and len(pilot.history("second")) == 1
    assert pilot.ask(mixed, "first", "P2", mode="P2", now=1040)["status"] == "blocked"
    assert provider.sent == ["P1", "P2"]


def test_p1_interprets_idiom_but_cannot_delete_second_need(tmp_path):
    catalog = Catalog(load_git(Path(os.environ["SATURN_SOURCE"])))

    def interpret(mode, payload):
        option = next(item for item in payload["allowed_options"] if item["attribute"] == "mass")
        return {"interpretation_status": "supported", "need_ids": ["n1"], "interpretations": [option]}

    pilot = Pilot(catalog, tmp_path / "pilot.sqlite", mock=interpret, mock_budget=1)
    question = "Сколько покажет на весах БКД-ПК-RF.2 и какое назначение СЛДКС-1?"
    result = pilot.ask(question, "s", "id", mode="P1")
    assert result["status"] == "answered"
    assert [need["attribute"] for need in result["question_needs"]] == ["mass", "purpose"]
