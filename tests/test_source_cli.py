import subprocess
import sys

import pytest


@pytest.mark.parametrize(("arguments", "hint"), [
    (["import", "absent-source"], "git init"),
    (["serve", "--lab", "--enable-deepseek"], "import ../saturn-pilot-source"),
])
def test_missing_sources_report_setup_instead_of_traceback(tmp_path, arguments, hint):
    result = subprocess.run(
        [sys.executable, "-m", "ds_pilot", "--data", str(tmp_path), *arguments],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert hint in result.stderr
    assert "Traceback" not in result.stderr
    assert "DeepSeek API Key" not in result.stdout + result.stderr
