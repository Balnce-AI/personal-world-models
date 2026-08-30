import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_registered_component_statuses_are_valid():
    result = subprocess.run(
        [sys.executable, "scripts/check_status.py", "governance/components.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_status_linter_rejects_unknown_axis_value(tmp_path):
    registry = {
        "schema_version": "1.0.0",
        "components": [
            {
                "id": "invalid",
                "path": "README.md",
                "truth_plane": "MADE_UP",
                "evidence_status": "REAL",
                "publication_class": "PUBLIC_FULL",
                "assurance_level": "BASELINE_CAPTURED",
                "release_disposition": "RELEASABLE",
                "included_in_release": True,
                "last_verified": "2026-08-29",
                "source_refs": ["public-v1-archive"],
                "limitations": ["Test fixture"],
            }
        ],
    }
    path = tmp_path / "components.json"
    path.write_text(json.dumps(registry))

    result = subprocess.run(
        [sys.executable, "scripts/check_status.py", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "truth_plane" in result.stderr


def test_status_linter_rejects_held_release_component(tmp_path):
    registry = {
        "schema_version": "1.0.0",
        "components": [
            {
                "id": "held",
                "path": "README.md",
                "truth_plane": "OPERATIONALIZING",
                "evidence_status": "SPECIFIED",
                "publication_class": "PUBLIC_INTERFACE_ONLY",
                "assurance_level": "NOT_ASSESSED",
                "release_disposition": "HOLD_IP",
                "included_in_release": True,
                "last_verified": "2026-08-29",
                "source_refs": ["Package One"],
                "limitations": ["Test fixture"],
            }
        ],
    }
    path = tmp_path / "components.json"
    path.write_text(json.dumps(registry))

    result = subprocess.run(
        [sys.executable, "scripts/check_status.py", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "included_in_release" in result.stderr


def test_v1_ledger_covers_archive_and_historical_union():
    ledger = json.loads((ROOT / "migration/v1_file_ledger.json").read_text())
    entries = ledger["files"]

    assert ledger["archive_file_count"] == 97
    assert ledger["union_file_count"] == 116
    assert sum(entry["in_archive_head"] for entry in entries) == 97
    assert len({entry["path"] for entry in entries}) == 116
    assert all(entry["disposition"] in ledger["allowed_dispositions"] for entry in entries)


def test_v1_ledger_matches_pinned_git_trees():
    ledger = json.loads((ROOT / "migration/v1_file_ledger.json").read_text())
    entries = {entry["path"]: entry for entry in ledger["files"]}

    def tree_paths(revision):
        result = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", revision],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return set(result.stdout.splitlines())

    archive_paths = tree_paths(ledger["archive_commit"])
    initial_paths = tree_paths(ledger["initial_public_corpus_commit"])

    assert set(entries) == archive_paths | initial_paths
    assert {path for path, entry in entries.items() if entry["in_archive_head"]} == archive_paths
    assert {path for path, entry in entries.items() if entry["in_initial_public_corpus"]} == initial_paths


def test_v1_archive_manifest_pins_recoverable_commit():
    manifest = json.loads((ROOT / "migration/V1_ARCHIVE_MANIFEST.json").read_text())

    assert manifest["tag"] == "public-v1-archive"
    assert manifest["commit"] == "363fe941b6c71a0235b8479a33ea7a7286e7dbe2"
    assert manifest["sha256"] == "38b71f7274d65dba9260042da779386012ec5e16c8f841a0479e376881b4a0e8"
    assert manifest["tracked_file_count"] == 97
