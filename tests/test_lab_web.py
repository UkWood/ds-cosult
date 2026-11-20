"""LAB web boundary tests use only local state and an offline catalog."""
import os
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

from ds_pilot.catalog import Catalog, load_git
from ds_pilot.engine import Pilot
from ds_pilot.web import create_app


@pytest.fixture
def pilot(tmp_path):
    return Pilot(Catalog(load_git(Path(os.environ["SATURN_SOURCE"]))), tmp_path / "lab.sqlite", lab=True)


def test_loopback_and_provider_controls(pilot):
    client = TestClient(create_app(pilot))
    for headers in ({"Host":"outside.invalid"}, {"X-Forwarded-For":"127.0.0.1"},
                    {"Forwarded":"for=127.0.0.1"}, {"Origin":"https://example.invalid"}):
        response = client.get("/", headers=headers)
        assert response.status_code == 403 and response.headers["Cache-Control"] == "no-store"
    client.get("/")
    state = client.get("/api/session").json()
    assert state["lab"] and not state["live"] and "budget" not in state
    assert state["scope"]["sources"] >= 2
    req = {"question": "Какая масса БКД-ПК-RF.2?", "request_id": state["next_request"], "mode": "P1"}
    assert client.post("/api/ask", json=req).status_code == 403
    assert client.get("/api/history").json()["turns"] == []
    req.update(mode="P0", dialog=state["dialog"])
    assert client.post("/api/dialog/new", json={}).status_code == 200
    assert client.post("/api/ask", json=req).status_code == 409


def test_policy_session_privacy(pilot):
    policy = Pilot(pilot.catalog, pilot.database.with_name("policy.sqlite"))
    policy.ask("Какая масса БКД-ПК-RF.2?", "cli", "cli-1")
    client = TestClient(create_app(policy))
    client.cookies.set("pilot_session", "cli")
    assert client.get("/api/history").status_code == 403
    client.get("/")
    assert client.get("/api/history").json() == {"turns":[]}
    assert client.post("/api/recover", json={"code":"anything"}).status_code == 403
    assert client.post("/api/dialog/reset", json={}).status_code == 403


def test_nonloopback_lab_bind_rejected():
    run = subprocess.run([sys.executable, "-m", "ds_pilot", "serve", "--lab", "--host", "0.0.0.0"],
                         capture_output=True, text=True, timeout=10)
    assert run.returncode and "--host" in run.stderr
