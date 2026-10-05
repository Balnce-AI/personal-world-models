from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def main() -> int:
    runner = Path.cwd() / "scripts" / "pwm_conformance.py"
    if not runner.is_file():
        raise SystemExit("pwm-conformance must run from a personal-world-models checkout")
    specification = importlib.util.spec_from_file_location("pwm_conformance_runner", runner)
    if specification is None or specification.loader is None:
        raise SystemExit("unable to load conformance runner")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module.main()
