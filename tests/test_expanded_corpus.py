import os
from pathlib import Path

import pytest

from ds_pilot.catalog import Catalog, PINS, import_checkout, load_git, load_local
from ds_pilot.discovery import pins
from ds_pilot.engine import Pilot


@pytest.fixture(scope="module")
def files():
    return load_git(Path(os.environ["SATURN_SOURCE"]))


def test_import_is_offline_and_checks_every_source(tmp_path):
    checkout = Path(os.environ["SATURN_SOURCE"])
    imported = import_checkout(checkout, tmp_path)
    assert imported.manifest() == load_local(tmp_path).manifest()
    assert len(imported.coverage["site_files"]) == len(pins()["sources"]) == 30
    target = tmp_path / imported.coverage["bundle"] / "products.bkd-me.md"
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="Invalid pinned blob"):
        load_local(tmp_path)


def test_separate_component_and_evidence_gain(files, tmp_path):
    question = "Какая масса у БКД-МЕ?"
    baseline = Catalog({key: files[key] for key in PINS})
    old = Pilot(baseline, tmp_path / "old.sqlite").ask(question, "local", "q")
    assert not old.get("verified_claims")
    current = Pilot(Catalog(files), tmp_path / "new.sqlite").ask(question, "local", "q")
    assert current["status"] == "answered"
    claim, = current["verified_claims"]
    assert "2 кг" in claim["text"]
    proof = claim["citation"]
    assert proof["path"] == "src/content/products/bkd-me.md"
    assert proof["snippet"] in files["products.bkd-me"].decode()
    assert proof["locator"] == "mass_kg"


@pytest.mark.parametrize(("scope","expected","forbidden"), [
    ("первого поколения", "ЛИФТ-3", "БКД-МЕ"),
    ("второго поколения", "ЛИФТ-4", "БКД-Р"),
    ("М2 без компьютера", "БКД-Р", "ЛИФТ-4"),
    ("М2", "ЛИФТ-4", "БКД-Р"),
])
def test_source_scoped_composition(files, tmp_path, scope, expected, forbidden):
    result = Pilot(Catalog(files), tmp_path/"pilot.sqlite").ask(
        f"Какой состав у СЛДКС-1 {scope}?", "local","q")
    assert result["status"] == "answered"
    assert expected in result["text"] and forbidden not in result["text"]
    assert len({c["configuration"] for c in result["verified_claims"]}) == 1


def test_lexical_rows_are_only_candidates_and_ledger_scans_all_values(files,tmp_path):
    catalog = Catalog(files)
    matches = catalog.search("количество тип блока назначение", "articles.prostaya-sistema-dispetcherizatsii-liftov", 20)
    assert any("Количество:" in row["excerpt"] and "Назначение:" in row["excerpt"] for row in matches)
    assert all(row["role"] == "retrieval_candidate" and "#L" in row["url"] for row in matches)
    # An exact structured mass and a qualified upper bound coexist in the same dossier.
    result = Pilot(catalog,tmp_path/"pilot.sqlite").ask("Какая масса БГС-ПМ?", "local","q")
    assert result["reason_code"] == "applicable_source_conflict"
    assert {p["citation"]["locator"].split("[")[0] for p in result["conflict_positions"]} == {"mass_kg","specs"}
    assert not result["verified_claims"]


def test_incompatible_variant_qualifiers_cannot_select_a_composition(files, tmp_path):
    pilot = Pilot(Catalog(files), tmp_path/"pilot.sqlite")
    answer = pilot.ask("Состав первого поколения СЛДКС-1 серии М2?", "local","q")
    assert answer["reason_code"] == "ambiguous_variant"
    assert not answer["verified_claims"]
