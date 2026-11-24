"""Shared test helpers and context for Phase 1 verification."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

UINT64_MAX = (1 << 64) - 1
UINT32_MAX = (1 << 32) - 1


@dataclass
class TestContext:
    root: Path
    verbose: bool = False
    log_lines: list[str] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    @property
    def agent_dir(self) -> Path:
        return self.root / "edr-agent"

    def emit(self, line: str) -> None:
        print(line)
        self.log_lines.append(line)

    def ok(self, name: str, detail: str = "") -> None:
        self.passed += 1
        suffix = f" - {detail}" if detail else ""
        self.emit(f"[PASS] {name}{suffix}")

    def fail(self, name: str, detail: str) -> None:
        self.failed += 1
        self.emit(f"[FAIL] {name}: {detail}")

    def skip(self, name: str, reason: str) -> None:
        self.skipped += 1
        self.emit(f"[SKIP] {name}: {reason}")

    def run_cmd(
        self,
        cmd: list[str],
        cwd: Path,
        env_extra: dict[str, str] | None = None,
    ) -> tuple[int, str, str]:
        env = os.environ.copy()
        if env_extra:
            env.update(env_extra)
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if self.verbose:
                if proc.stdout.strip():
                    self.emit(f"    [stdout] {proc.stdout.strip()}")
                if proc.stderr.strip():
                    self.emit(f"    [stderr] {proc.stderr.strip()}")
            return proc.returncode, proc.stdout, proc.stderr
        except OSError as exc:
            return 127, "", str(exc)
