import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_local_links_resolve():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"\[[^]]+\]\(([^)]+)\)", readme)
    local = [link.split("#", 1)[0] for link in links if not re.match(r"(?:https?://|mailto:|#)", link)]
    assert local
    assert not [link for link in local if not (ROOT / link).exists()]


def test_publication_metadata_matches_release_boundary():
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert "cff-version: 1.2.0" in citation
    assert "version: 0.2.0" in citation
    assert "repository-code: \"https://github.com/Balnce-AI/personal-world-models\"" in citation

    result = json.loads((ROOT / "experiments/results/fixture-control.json").read_text())
    assert result["gitDirty"] is False
    # The fixture is immutable evidence generated from the clean claims milestone.
    assert result["gitCommit"] == "244e522391258f6e83e6c433a6c8e8d940da8f9a"

    suite = ROOT / "conformance/vectors/signed-semantic-suite.json"
    assert hashlib.sha256(suite.read_bytes()).hexdigest() == "f1fda71d804a3e03ec3157ba11d10696e8f7c57845b622f2ef4c048e6289778b"


def test_tracked_public_tree_has_no_machine_local_or_parent_control_paths():
    paths = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    forbidden = ("/" + "Users/", "/var/" + "folders/", "../MASTER_" + "INSTRUCTION.md")
    findings = []
    for relative in paths:
        path = ROOT / relative
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in forbidden:
            if marker in content:
                findings.append((relative, marker))
    assert findings == []
