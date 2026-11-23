"""Offline coverage of owner activation, local materials, and the listen socket."""
from datetime import datetime, timezone
from hashlib import sha1, sha256
import io
from pathlib import Path
import socket

import pytest


def test_live_boot_on_non_wsl_stops_before_checkout(monkeypatch, capsys):
    from scripts.validation import launch_dc05a as launcher

    monkeypatch.setattr(launcher, "trusted_wsl", lambda: False)
    monkeypatch.setattr(launcher, "prepare_checkout", lambda *_: pytest.fail("unexpected GitHub fetch"))
    raw = Path(launcher.__file__).read_bytes()
    blob = sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()

    assert launcher.main(["--commit", "a" * 40, "--blob", blob, "--live"]) == 2
    assert "trusted_wsl_required" in capsys.readouterr().err


def test_listen_socket_is_held_then_released_on_loopback():
    from scripts.validation import launch_dc05a as launcher

    with launcher.listen_on_loopback(0) as reserved:
        addr, port = reserved.getsockname()
        assert (addr, reserved.family) == ("127.0.0.1", socket.AF_INET)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as collision:
            with pytest.raises(OSError):
                collision.bind(("127.0.0.1", port))

    with launcher.listen_on_loopback(port) as rebound:
        assert rebound.getsockname() == ("127.0.0.1", port)


def test_port_conflict_precedes_preflight_and_live_inputs(tmp_path, monkeypatch):
    from scripts.validation import launch_dc05a as launcher

    monkeypatch.setattr(launcher, "operator_activation", lambda *_: pytest.fail("unexpected activation prompt"))
    monkeypatch.setattr(launcher, "validate_dependencies", lambda *_: pytest.fail("unexpected dependency work"))
    with launcher.listen_on_loopback(0) as reserved:
        port = reserved.getsockname()[1]
        with pytest.raises(launcher.LaunchError, match="loopback_port_unavailable"):
            launcher.serve_checkout(tmp_path, tmp_path, live=True, port=port)


@pytest.mark.parametrize(("raw", "micro_usd"), [("0.000001", 1), ("0.75", 750000), ("5,05", 5050000)])
def test_budget_parses_exactly_without_a_default(raw, micro_usd):
    from scripts.validation import launch_dc05a as launcher

    assert launcher.parse_budget(raw) == micro_usd


@pytest.mark.parametrize("raw", ["", "0", "0.0000001", "-0.25", "1e4", "NaN", "1."])
def test_invalid_budget_blocks_activation(raw):
    from scripts.validation import launch_dc05a as launcher

    with pytest.raises(launcher.LaunchError, match="session_budget_invalid"):
        launcher.parse_budget(raw)


@pytest.mark.parametrize(("typed", "failure"), [("", "live_activation_not_confirmed"),
                                                ("LIVE\n\n", "session_budget_invalid")])
def test_owner_consent_and_nonempty_cap_precede_hidden_key(typed, failure):
    from scripts.validation import launch_dc05a as launcher

    def key_prompt(*_args, **_kwargs):
        pytest.fail("unexpected key prompt")

    with pytest.raises(launcher.LaunchError, match=failure):
        launcher.operator_activation(io.StringIO(typed), io.StringIO(), key_reader=key_prompt)


def test_owner_enters_exactly_one_hidden_key_after_budget(monkeypatch):
    from scripts.validation import launch_dc05a as launcher

    monkeypatch.setattr(launcher, "utc_now", lambda: datetime(2026, 11, 24, tzinfo=timezone.utc))
    output = io.StringIO()
    calls = []

    def key_prompt(prompt, *, stream):
        assert stream is output
        assert "KEY" in prompt
        calls.append(prompt)
        return "private-dummy-test-key"

    cap, key = launcher.operator_activation(io.StringIO("LIVE\n19.25\n"), output, key_reader=key_prompt)

    assert cap == 19250000 and key == "private-dummy-test-key" and len(calls) == 1
    assert key not in output.getvalue()


def test_expired_provider_contract_blocks_live_activation():
    from scripts.validation import launch_dc05a as launcher

    launcher.check_contract(datetime(2026, 11, 24, tzinfo=timezone.utc))
    with pytest.raises(launcher.LaunchError, match="provider_contract_expired_or_unreviewed"):
        launcher.check_contract(datetime(2026, 12, 24, tzinfo=timezone.utc))


def test_partial_but_pinned_cache_can_be_discovered(tmp_path):
    from scripts.validation import launch_dc05a as launcher

    cache = tmp_path / "prepared-cache"
    cache.mkdir()
    tokenizer = b"reviewed tokenizer"
    pdf = b"approved first pdf"
    (cache / "audit.json").write_text("{}")
    (cache / "token.json").write_bytes(tokenizer)
    sha = sha256(pdf).hexdigest()
    (cache / f"{sha}.pdf").write_bytes(pdf)

    identified = launcher.discover_cache(
        tmp_path, "token.json", sha256(tokenizer).hexdigest(), {sha: len(pdf), "a" * 64: 123}
    )

    assert identified == cache


def test_truncated_cap_never_triggers_key_prompt(monkeypatch):
    from scripts.validation import launch_dc05a as launcher

    monkeypatch.setattr(launcher, "utc_now", lambda: datetime(2026, 11, 24, tzinfo=timezone.utc))

    def key_prompt(*_args, **_kwargs):
        pytest.fail("truncated cap unexpectedly admitted")

    typed = io.StringIO("LIVE\n" + "9" * 100 + "\n")
    with pytest.raises(launcher.LaunchError, match="session_budget_invalid"):
        launcher.operator_activation(typed, io.StringIO(), key_reader=key_prompt)


def test_trial_state_refuses_to_open_a_link_to_historical_state(tmp_path, monkeypatch):
    from scripts.validation import launch_dc05a as launcher

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    history = tmp_path / ".local/state/ds-dc02"
    history.mkdir(mode=0o700, parents=True)
    (history.parent / "ds-dc05a").symlink_to(history, target_is_directory=True)

    with pytest.raises(launcher.LaunchError, match="trial_state_not_private"):
        with launcher.trial_state():
            pytest.fail("linked state unexpectedly admitted")

    assert not list(history.iterdir())


@pytest.mark.parametrize("live", [False, True])
def test_browser_token_is_only_passed_to_live_app_and_written_to_tty(tmp_path, monkeypatch, capsys, live):
    import uvicorn

    from ds_dc import trial, trial_native, trial_web
    from scripts.validation import launch_dc05a as launcher

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(launcher, "validate_dependencies", lambda _: None)
    monkeypatch.setattr(launcher, "check_site", lambda _: None)
    monkeypatch.setattr(launcher, "matches_file", lambda *_: True)
    monkeypatch.setattr(launcher, "trusted_wsl", lambda: True)
    monkeypatch.setattr(launcher, "utc_now", lambda: datetime(2026, 11, 24, tzinfo=timezone.utc))
    monkeypatch.setattr(trial, "load_trial_materials", lambda *_: ({}, {}))
    launches = []
    provider_settings = []

    def activate():
        assert live
        return 250000, "private-dummy-test-key"

    def app(_consultant, _journal, **kwargs):
        launches.append(kwargs)

    class Native:
        mode = "live"

        def __init__(self, _cache, _directory, _cap, **kwargs):
            provider_settings.append(kwargs)

        @staticmethod
        def check_state(_directory):
            return False

    class Server:
        def __init__(self, _config):
            self.started = False

        def run(self, *, sockets):
            assert len(sockets) == 1
            self.started = True

    tty = tmp_path / "mock-terminal"

    def open_terminal(path, *args, **kwargs):
        assert path == "/dev/tty"
        return tty.open(*args, **kwargs)

    monkeypatch.setattr(launcher, "activate_from_tty", activate)
    monkeypatch.setattr(launcher, "open", open_terminal, raising=False)
    monkeypatch.setattr(trial_native, "TrialNative", Native)
    monkeypatch.setattr(trial_web, "create_app", app)
    monkeypatch.setattr(uvicorn, "Server", Server)

    launcher.serve_checkout(tmp_path, tmp_path, live=live, port=0)

    args, = launches
    captured = capsys.readouterr()
    output = captured.out + captured.err
    if live:
        token = args["owner_token"]
        assert len(token) >= 43
        address = f"http://127.0.0.1:0/#owner={token}"
        message = tty.read_text()
        assert address in message
        assert token not in output
        assert "private-dummy-test-key" not in message + output
        settings, = provider_settings
        assert settings["expires_at"] == datetime(2026, 12, 23, 5, 13, 43, tzinfo=timezone.utc).timestamp()
    else:
        assert args.get("owner_token") is None
        assert "http://127.0.0.1:0" in output and "#owner=" not in output
        assert not tty.exists()
        assert provider_settings == []


def test_preflight_requires_prlimit_for_pdf_verification(tmp_path, monkeypatch):
    from scripts.validation import launch_dc05a as launcher

    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(launcher.sys, "version_info", (3, 12, 0))
    monkeypatch.setattr(launcher.sys, "prefix", str(tmp_path))
    monkeypatch.setattr(launcher.shutil, "which", lambda name: None if name == "prlimit" else name)

    with pytest.raises(launcher.LaunchError, match="trial_dependency_program_missing"):
        launcher.validate_dependencies(tmp_path)
