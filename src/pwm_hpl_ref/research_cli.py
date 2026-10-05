from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .foundation_models import OllamaModel, OpenAICompatibleModel
from .research import FixtureControlModel, generate_coverage, run_experiment, write_result


def select_model(spec: str, base_url: str | None):
    if spec == "fixture-control":
        return FixtureControlModel()
    provider, separator, model_id = spec.partition(":")
    if not separator or not model_id:
        raise SystemExit("--model must be fixture-control, ollama:MODEL, or openai:MODEL")
    if provider == "ollama":
        return OllamaModel(model_id, base_url or "http://localhost:11434/v1")
    if provider == "openai":
        if not base_url:
            raise SystemExit("--base-url is required for an OpenAI-compatible provider")
        return OpenAICompatibleModel(model_id, base_url, os.getenv("OPENAI_API_KEY"))
    raise SystemExit(f"unsupported provider: {provider}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reproducible PWM research experiments")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--persona", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--condition", action="append")
    run.add_argument("--model", default="fixture-control")
    run.add_argument("--base-url")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--repetitions", type=int, default=1)
    compare = subparsers.add_parser("compare")
    compare.add_argument("results", nargs="+", type=Path)
    coverage = subparsers.add_parser("coverage")
    coverage.add_argument("--corpus", type=Path, required=True)
    coverage.add_argument("--personas", type=Path, required=True)
    coverage.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "run":
        conditions = tuple(args.condition) if args.condition else None
        model = select_model(args.model, args.base_url)
        result = (
            run_experiment(args.persona, model, conditions=conditions, seed=args.seed, repetitions=args.repetitions)
            if conditions
            else run_experiment(args.persona, model, seed=args.seed, repetitions=args.repetitions)
        )
        write_result(result, args.output)
        print(json.dumps({"experimentId": result["experimentId"], "output": str(args.output)}))
    elif args.command == "compare":
        summaries = []
        for path in args.results:
            result = json.loads(path.read_text(encoding="utf-8"))
            summaries.append({"experimentId": result["experimentId"], "runs": result["runs"]})
        print(json.dumps(summaries, indent=2, sort_keys=True))
    else:
        result = generate_coverage(args.corpus, args.personas.glob("*.json"))
        write_result(result, args.output)
        print(json.dumps({"coverageHash": result["coverageHash"], "output": str(args.output)}))
