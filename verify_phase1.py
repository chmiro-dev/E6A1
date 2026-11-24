#!/usr/bin/env python3
"""Thin CLI runner for the modular E6A1 Phase 1 test suite."""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.phase1 import (  # noqa: E402
    TestContext,
    run_build_isolation_tests,
    run_config_tests,
    run_schema_tests,
)

SUITES = {
    "schemas": run_schema_tests,
    "configs": run_config_tests,
    "build": run_build_isolation_tests,
}


def write_log(log_path: Path | None, root: Path, lines: list[str]) -> None:
    if not log_path:
        return
    resolved = log_path if log_path.is_absolute() else root / log_path
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[LOG] Saved verification output to {resolved}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run modular Phase 1 verification suites for E6A1."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT_DIR,
        help="Top-level project root directory.",
    )
    parser.add_argument(
        "--suite",
        choices=["all", *SUITES.keys()],
        default="all",
        help="Run a specific test module or all suites.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Optional output log path (e.g., logs/phase1_verify.log).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print command stdout/stderr details.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"[ERROR] Project root not found: {root}")

    ctx = TestContext(root=root, verbose=args.verbose)
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    ctx.emit(f"Phase 1 Verification Log - {ts}")
    ctx.emit(f"Project Root: {root} (OS={sys.platform}) | Suite: {args.suite}")
    ctx.emit("-" * 72)

    selected = list(SUITES.values()) if args.suite == "all" else [SUITES[args.suite]]
    for fn in selected:
        fn(ctx)

    ctx.emit("-" * 72)
    ctx.emit(f"Summary: {ctx.passed} passed, {ctx.failed} failed, {ctx.skipped} skipped")
    write_log(args.log_file, root, ctx.log_lines)
    raise SystemExit(1 if ctx.failed > 0 else 0)


if __name__ == "__main__":
    main()
