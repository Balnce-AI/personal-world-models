import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_rust_dependency_licenses_are_declared(tmp_path: Path):
    output = tmp_path / "rust-licenses.json"
    result = subprocess.run(
        [sys.executable, "scripts/rust_supply_chain.py", "--output", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["schema_version"] == "1.0.0"
    assert report["dependencies"]
    assert all(item["license"] for item in report["dependencies"])
