"""Offline validation of real pins and mock-only protocol contracts."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from bundle import archive, sums
from compile_d import graph_estimate
from protocol import Stop, encode, offline, save, sha, kernel_release, runtime_digest
from r4_a import plan
from sources import verify


def run(args):
    if sys.version_info < (3, 12):
        raise Stop("Use Python 3.12+ from the experiment venv")
    os.umask(0o077)
    offline()
    identity = verify(args.sources, args.site)
    packages = [args.sources, *args.additional_source]
    package_env = (os.pathsep.join(str(path.resolve()) for path in packages)
                   if len(packages) > 1 else "")
    graph = graph_estimate(args.sources)
    experiment = plan(args.sources)
    args.reports = args.reports.resolve()
    if args.reports.exists():
        raise Stop("Choose a fresh preflight reports path")
    print("Pilot base graph " + encode(graph).decode(), flush=True)
    log = subprocess.run([sys.executable, "-m", "unittest", "-v", "test_d", "test_universal", "test_r4", "test_r4_c", "test_compile_release"],
                         cwd=Path(__file__).resolve().parent, check=True,
                         env=dict(os.environ, DX02_PREFLIGHT_SOURCES=str(args.sources.resolve()),
                                  DX02_PREFLIGHT_SITE=str(args.site.resolve()),
                                  UTKC_ACCEPTANCE_PACKAGES=package_env,
                                  DX02_MOCK_EVIDENCE=str(args.reports)),
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sys.stdout.flush()
    sys.stdout.buffer.write(log.stdout)
    evidence = {"snapshot": identity, "offline": "seccomp: socket EPERM", "paid_calls": 0,
                "transport": "mock only", "r4_c_sse": True, "r4_b_int": True, "package_count": len(packages), "graph": graph, "experiment_sha256": sha(encode(experiment)), "kernel": kernel_release(), "runtime": runtime_digest(), "status": "ENGINEERING_PREFLIGHT_ONLY"}
    entries = {"preflight.json": encode(evidence), "tests.txt": log.stdout,
               "r4-a-plan.json": encode(experiment)}
    entries["SHA256SUMS"] = sums(entries)
    archive(args.reports / "DS-DX-02-D-preflight.zip", entries)
    save(args.reports / "preflight.json", evidence)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("sources", "site", "reports"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--additional-source", action="append", type=Path, default=[])
    try:
        run(parser.parse_args())
    except (Stop, subprocess.CalledProcessError) as error:
        if getattr(error, "stdout", None):
            sys.stderr.buffer.write(error.stdout)
        raise SystemExit(str(error)) from None
