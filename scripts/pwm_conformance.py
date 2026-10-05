#!/usr/bin/env python3
"""Language-neutral PWM conformance runner and semantic differ."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "conformance" / "manifest.json"
DEFAULT_IMPLEMENTATIONS = ROOT / "conformance" / "implementations"
CONTRACT = "pwm-conformance-result-v1"
MISSING = object()


class RunnerError(Exception):
    pass


@dataclass(frozen=True)
class Job:
    suite_id: str
    profile: str
    bundle: Path
    expected: dict[str, dict[str, Any]]


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunnerError(f"cannot read JSON {path}: {error}") from error


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        )
    except (TypeError, ValueError) as error:
        raise RunnerError(f"value is not canonical JSON: {error}") from error


def load_implementations(directory: Path) -> dict[str, dict[str, Any]]:
    implementations: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json")):
        manifest = load_json(path)
        required = {"name", "version", "language", "command", "profiles"}
        if not isinstance(manifest, dict) or not required <= manifest.keys():
            raise RunnerError(f"invalid adapter manifest {path}: required fields are {sorted(required)}")
        if not all(isinstance(manifest[key], str) and manifest[key] for key in ("name", "version", "language")):
            raise RunnerError(f"invalid adapter manifest {path}: name, version, and language must be strings")
        command = manifest["command"]
        profiles = manifest["profiles"]
        if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
            raise RunnerError(f"invalid adapter manifest {path}: command must be a non-empty string array")
        if not any("{bundle}" in part for part in command):
            raise RunnerError(f"invalid adapter manifest {path}: command must contain {{bundle}}")
        if not isinstance(profiles, list) or not profiles or not all(isinstance(item, str) for item in profiles):
            raise RunnerError(f"invalid adapter manifest {path}: profiles must be a non-empty string array")
        if manifest["name"] in implementations:
            raise RunnerError(f"duplicate implementation name: {manifest['name']}")
        implementations[manifest["name"]] = manifest
    return implementations


def resolve_suites(manifest: dict[str, Any], target: str) -> list[dict[str, Any]]:
    suites = {suite["id"]: suite for suite in manifest.get("suites", [])}
    if target in suites:
        return [suites[target]]
    for level in manifest.get("levels", []):
        if level.get("id") == target:
            return [suites[suite_id] for suite_id in level["requiredSuites"]]
    raise RunnerError(f"unknown conformance level or suite: {target}")


def suite_jobs(suite: dict[str, Any], root: Path) -> list[Job]:
    fixtures = [(root / fixture).resolve() for fixture in suite["fixtures"]]
    documents = [(path, load_json(path)) for path in fixtures]
    referenced = {
        (root / document["fixture"]).resolve()
        for _, document in documents
        if isinstance(document, dict) and isinstance(document.get("fixture"), str)
    }
    jobs: list[Job] = []
    for path, document in documents:
        if isinstance(document, dict) and isinstance(document.get("cases"), list):
            case_key = "case_id" if document.get("format") == "signed-semantic-suite-v1" or all("case_id" in case for case in document["cases"]) else "id"
            expected = {
                case[case_key]: {key: value for key, value in case["expected"].items() if key != "invariants"}
                for case in document["cases"]
            }
            jobs.append(Job(suite["id"], suite["profile"], path, expected))
        elif isinstance(document, dict) and isinstance(document.get("fixture"), str):
            expected = {
                path.stem: {
                    key: value
                    for key, value in document.items()
                    if key not in {"profile", "fixture"}
                }
            }
            jobs.append(Job(suite["id"], suite["profile"], (root / document["fixture"]).resolve(), expected))
        elif path not in referenced:
            # Some evidence corpora have no normative per-case outcome and cannot be scored.
            continue
    if not jobs:
        raise RunnerError(f"suite {suite['id']} has no runnable expectations")
    return jobs


def invoke_adapter(implementation: dict[str, Any], job: Job) -> dict[str, Any]:
    if job.profile not in implementation["profiles"]:
        raise RunnerError(
            f"implementation {implementation['name']} does not support profile {job.profile}"
        )
    substitutions = {
        "bundle": str(job.bundle),
        "profile": job.profile,
        "suite": job.suite_id,
        "python": sys.executable,
        "root": str(ROOT),
    }
    command = []
    for part in implementation["command"]:
        for placeholder, value in substitutions.items():
            part = part.replace("{" + placeholder + "}", value)
        command.append(part)
    try:
        completed = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RunnerError(f"adapter {implementation['name']} could not run: {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no diagnostic output"
        raise RunnerError(f"adapter {implementation['name']} exited {completed.returncode}: {detail}")
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RunnerError(f"adapter {implementation['name']} emitted invalid JSON: {error}") from error
    if completed.stdout != canonical_json(output) + "\n":
        raise RunnerError(
            f"adapter {implementation['name']} output is not canonical JSON "
            "(UTF-8, sorted object keys, compact separators, one trailing newline required)"
        )
    validate_contract(output, implementation["name"], job)
    return output


def validate_contract(output: Any, name: str, job: Job) -> None:
    if not isinstance(output, dict):
        raise RunnerError(f"adapter {name} output must be an object")
    if output.get("contract") != CONTRACT:
        raise RunnerError(f"adapter {name} output contract must be {CONTRACT}")
    if output.get("profile") != job.profile or output.get("suite") != job.suite_id:
        raise RunnerError(f"adapter {name} output profile or suite does not match the invocation")
    cases = output.get("cases")
    if not isinstance(cases, list):
        raise RunnerError(f"adapter {name} output cases must be an array")
    ids: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not isinstance(case.get("actual"), dict):
            raise RunnerError(f"adapter {name} cases[{index}] must contain string id and object actual")
        if case["id"] in ids:
            raise RunnerError(f"adapter {name} emitted duplicate case id {case['id']}")
        ids.add(case["id"])
        if "events" in case and not isinstance(case["events"], list):
            raise RunnerError(f"adapter {name} case {case['id']} events must be an array")


def _difference(path: str, expected: Any, actual: Any) -> str | None:
    if expected == actual:
        return None
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(expected.keys() | actual.keys()):
            left = expected.get(key, MISSING)
            right = actual.get(key, MISSING)
            child = f"{path}.{key}" if path else key
            if left is MISSING:
                return f"{child}: unexpected {right!r}"
            if right is MISSING:
                return f"{child}: missing; expected {left!r}"
            difference = _difference(child, left, right)
            if difference:
                return difference
    elif isinstance(expected, list) and isinstance(actual, list):
        for index, (left, right) in enumerate(zip(expected, actual)):
            difference = _difference(f"{path}[{index}]", left, right)
            if difference:
                return difference
        return f"{path}: expected {len(expected)} items, actual {len(actual)} items"
    return f"{path}: expected {expected!r}, actual {actual!r}"


SECTIONS = (
    ("materialized state", ("materialized", "materializedState")),
    ("query", ("query",)),
    ("privacy", ("privacy",)),
    ("contradictions", ("contradictions",)),
    ("topology", ("topology",)),
    ("HPL", ("hpl", "projection")),
    ("error code", ("error", "code")),
    ("canonical bytes", ("canonicalBytes", "canonical_bytes")),
)


def _lookup(document: Any, paths: tuple[str, ...]) -> tuple[str, Any]:
    if len(paths) == 2 and paths == ("error", "code"):
        error = document.get("error", MISSING) if isinstance(document, dict) else MISSING
        return "error.code", error.get("code", MISSING) if isinstance(error, dict) else MISSING
    if isinstance(document, dict):
        for path in paths:
            if path in document:
                return path, document[path]
    return paths[0], MISSING


def semantic_diff(expected: Any, actual: Any) -> list[str]:
    diagnostics: list[str] = []
    expected_events = expected.get("events", MISSING) if isinstance(expected, dict) else MISSING
    actual_events = actual.get("events", MISSING) if isinstance(actual, dict) else MISSING
    if isinstance(expected_events, list) and isinstance(actual_events, list):
        left = expected_events
        right = actual_events
        difference = _difference("events", left, right)
        if difference:
            index = 0
            while index < min(len(left), len(right)) and left[index] == right[index]:
                index += 1
            event = left[index] if index < len(left) else right[index] if index < len(right) else {}
            event_id = event.get("eventId", event.get("id", "<unknown>")) if isinstance(event, dict) else "<unknown>"
            diagnostics.append(f"first divergent event [{index}] {event_id}: {difference}")

    covered: set[str] = {"events"}
    for label, paths in SECTIONS:
        expected_path, left = _lookup(expected, paths)
        actual_path, right = _lookup(actual, paths)
        if left is MISSING and right is MISSING:
            continue
        covered.update(paths)
        difference = _difference(label, None if left is MISSING else left, None if right is MISSING else right)
        if difference:
            diagnostics.append(f"{label}: {difference}")

    if isinstance(expected, dict) and isinstance(actual, dict):
        remaining_expected = {key: value for key, value in expected.items() if key not in covered}
        remaining_actual = {key: value for key, value in actual.items() if key not in covered}
        difference = _difference("result", remaining_expected, remaining_actual)
    else:
        difference = _difference("result", expected, actual)
    if difference:
        diagnostics.append(difference)
    return diagnostics


def case_map(output: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in output["cases"]}


def verify_jobs(implementation: dict[str, Any], jobs: list[Job]) -> list[str]:
    failures: list[str] = []
    for job in jobs:
        actual_cases = case_map(invoke_adapter(implementation, job))
        for case_id in sorted(job.expected.keys() | actual_cases.keys()):
            if case_id not in job.expected:
                failures.append(f"{job.suite_id}/{case_id}: unexpected adapter result")
                continue
            if case_id not in actual_cases:
                failures.append(f"{job.suite_id}/{case_id}: missing adapter result")
                continue
            actual = actual_cases[case_id]["actual"]
            if "events" in actual_cases[case_id]:
                actual = {**actual, "events": actual_cases[case_id]["events"]}
            for diagnostic in semantic_diff(job.expected[case_id], actual):
                failures.append(f"{job.suite_id}/{case_id}: {diagnostic}")
    return failures


def command_verify(args: argparse.Namespace) -> int:
    manifest_path = Path(args.conformance_manifest).resolve()
    manifest = load_json(manifest_path)
    implementations = load_implementations(Path(args.implementations_dir).resolve())
    if args.implementation not in implementations:
        raise RunnerError(f"unknown implementation: {args.implementation}")
    suites = resolve_suites(manifest, args.profile)
    jobs = [job for suite in suites for job in suite_jobs(suite, manifest_path.parents[1])]
    failures = verify_jobs(implementations[args.implementation], jobs)
    if failures:
        print("FAIL")
        print("\n".join(failures))
        return 1
    print(f"PASS {args.implementation} {args.profile} ({sum(len(job.expected) for job in jobs)} cases)")
    return 0


def command_compare(args: argparse.Namespace) -> int:
    if len(args.implementations) < 2:
        raise RunnerError("compare requires at least two implementations")
    manifest_path = Path(args.conformance_manifest).resolve()
    manifest = load_json(manifest_path)
    suites = resolve_suites(manifest, args.suite)
    if len(suites) != 1:
        raise RunnerError("compare --suite must name one suite")
    implementations = load_implementations(Path(args.implementations_dir).resolve())
    unknown = [name for name in args.implementations if name not in implementations]
    if unknown:
        raise RunnerError(f"unknown implementation(s): {', '.join(unknown)}")
    jobs = suite_jobs(suites[0], manifest_path.parents[1])
    outputs: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
    for name in args.implementations:
        outputs[name] = {}
        for job in jobs:
            for case_id, case in case_map(invoke_adapter(implementations[name], job)).items():
                actual = case["actual"]
                if "events" in case:
                    actual = {**actual, "events": case["events"]}
                outputs[name][(str(job.bundle), case_id)] = actual
    failures: list[str] = []
    baseline = args.implementations[0]
    for other in args.implementations[1:]:
        keys = outputs[baseline].keys() | outputs[other].keys()
        for bundle, case_id in sorted(keys):
            left = outputs[baseline].get((bundle, case_id), MISSING)
            right = outputs[other].get((bundle, case_id), MISSING)
            for diagnostic in semantic_diff(left, right):
                failures.append(f"{case_id}: {baseline} vs {other}: {diagnostic}")
    if failures:
        print("DIVERGED")
        print("\n".join(failures))
        return 1
    print(f"PASS {', '.join(args.implementations)} agree on {args.suite}")
    return 0


def command_diff(args: argparse.Namespace) -> int:
    diagnostics = semantic_diff(load_json(Path(args.expected)), load_json(Path(args.actual)))
    if diagnostics:
        print("DIVERGED")
        print("\n".join(diagnostics))
        return 1
    print("PASS documents are semantically equal")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subcommands = result.add_subparsers(dest="command", required=True)

    verify = subcommands.add_parser("verify", help="verify one implementation against a level or suite")
    verify.add_argument("--implementation", required=True)
    verify.add_argument("--profile", required=True, help="conformance level ID or suite ID")
    verify.set_defaults(handler=command_verify)

    compare = subcommands.add_parser("compare", help="compare implementations on one suite")
    compare.add_argument("--implementations", nargs="+", required=True)
    compare.add_argument("--suite", required=True)
    compare.set_defaults(handler=command_compare)

    diff = subcommands.add_parser("diff", help="semantically compare two JSON result documents")
    diff.add_argument("--expected", required=True)
    diff.add_argument("--actual", required=True)
    diff.set_defaults(handler=command_diff)

    for subcommand in (verify, compare):
        subcommand.add_argument("--conformance-manifest", default=str(DEFAULT_MANIFEST))
        subcommand.add_argument("--implementations-dir", default=str(DEFAULT_IMPLEMENTATIONS))
    return result


def main() -> int:
    try:
        args = parser().parse_args()
        return args.handler(args)
    except RunnerError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
