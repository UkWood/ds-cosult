#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
exec "${DX02_PYTHON:-python3}" consult_d.py "$@"
