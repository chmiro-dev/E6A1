"""Makefile build and collector isolation tests (WBS 1.2.2 / 2.3.2)."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .common import TestContext


def run_build_isolation_tests(ctx: TestContext) -> None:
    makefile = ctx.agent_dir / "Makefile"
    if not makefile.is_file():
        ctx.fail("1.2.2 Makefile exists", f"Missing {makefile}")
        return

    make_bin = shutil.which("make") or shutil.which("mingw32-make")
    if not make_bin:
        ctx.skip("1.2.2 Makefile execution", "make not found on PATH")
        return

    rc, _, err = ctx.run_cmd([make_bin, "check-isolation"], cwd=ctx.agent_dir)
    if rc == 0:
        ctx.ok("1.2.2 / 2.3.2 make check-isolation (clean)")
    else:
        ctx.fail("1.2.2 / 2.3.2 make check-isolation (clean)", err.strip() or f"exit {rc}")

    with tempfile.TemporaryDirectory(prefix="e6a1_iso_") as tmpdir:
        tmp_agent = Path(tmpdir) / "edr-agent"
        shutil.copytree(
            ctx.agent_dir,
            tmp_agent,
            ignore=shutil.ignore_patterns("target", "bin", "dist", "__pycache__", ".git", "NUL"),
        )
        target_rs = tmp_agent / "collector" / "src" / "main.rs"
        original_rs = target_rs.read_text(encoding="utf-8")
        target_rs.write_text("use std::net::TcpStream;\n" + original_rs, encoding="utf-8")

        rc_neg, _, _ = ctx.run_cmd([make_bin, "check-isolation"], cwd=tmp_agent)
        if rc_neg != 0:
            ctx.ok("2.3.2 check-isolation negative test", f"Blocked forbidden import (exit {rc_neg})")
        else:
            ctx.fail("2.3.2 check-isolation negative test", "Expected non-zero exit for std::net::TcpStream")

    if shutil.which("go"):
        rc_go, _, err_go = ctx.run_cmd([make_bin, "build-core"], cwd=ctx.agent_dir)
        if rc_go == 0:
            ctx.ok("1.2.2 make build-core")
        else:
            ctx.fail("1.2.2 make build-core", err_go.strip() or f"exit {rc_go}")
    else:
        ctx.skip("1.2.2 make build-core", "go not found on PATH")

    if shutil.which("cargo"):
        rc_cargo, _, err_cargo = ctx.run_cmd([make_bin, "build-collector"], cwd=ctx.agent_dir)
        if rc_cargo == 0:
            ctx.ok("1.2.2 make build-collector")
        else:
            ctx.fail("1.2.2 make build-collector", err_cargo.strip() or f"exit {rc_cargo}")
    else:
        ctx.skip("1.2.2 make build-collector", "cargo not found on PATH")

    rc_rules, out_rules, err_rules = ctx.run_cmd([make_bin, "build-rules"], cwd=ctx.agent_dir)
    if rc_rules == 0:
        ctx.ok(
            "1.2.2 make build-rules (pre-5.2.1 skip)",
            out_rules.strip().splitlines()[-1] if out_rules.strip() else "exit 0",
        )
    else:
        ctx.fail("1.2.2 make build-rules (pre-5.2.1 skip)", err_rules.strip() or f"exit {rc_rules}")

    rc_clean, _, err_clean = ctx.run_cmd([make_bin, "clean"], cwd=ctx.agent_dir)
    bin_removed = not (ctx.agent_dir / "core" / "bin").exists()
    dist_removed = not (ctx.agent_dir / "rules" / "dist").exists()
    if rc_clean == 0 and bin_removed and dist_removed:
        ctx.ok("1.2.2 make clean", "core/bin and rules/dist cleaned")
    else:
        ctx.fail(
            "1.2.2 make clean",
            f"rc={rc_clean}, bin_removed={bin_removed}, dist_removed={dist_removed}, err={err_clean.strip()}",
        )
