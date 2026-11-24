"""Configuration and policy template tests (WBS 1.1.3)."""

from __future__ import annotations

import re
import shutil
from typing import Any

from .common import TestContext


def _coerce_scalar(raw: str) -> Any:
    val = raw.strip()

    # Strip unquoted trailing comments while respecting single/double quotes
    in_single = False
    in_double = False
    cleaned: list[str] = []
    for ch in val:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            break
        cleaned.append(ch)
    val = "".join(cleaned).strip()

    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if re.fullmatch(r"-?[0-9]+", val):
        return int(val)
    return val


def parse_subset_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    lines = text.splitlines()
    idx = 0

    while idx < len(lines):
        raw_line = lines[idx]
        idx += 1
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        container = stack[-1][1]

        if stripped.startswith("- "):
            item_rest = stripped[2:].strip()
            if isinstance(container, list):
                if ":" in item_rest:
                    k, v = item_rest.split(":", 1)
                    obj: dict[str, Any] = {k.strip(): _coerce_scalar(v)}
                    container.append(obj)
                    stack.append((indent, obj))
                else:
                    container.append(_coerce_scalar(item_rest))
            continue

        if ":" in stripped:
            key, rest = stripped.split(":", 1)
            key = key.strip()
            val_str = rest.strip()
            val_no_comment = _coerce_scalar(val_str) if val_str else ""

            next_is_list = False
            peek = idx
            while peek < len(lines):
                p_line = lines[peek].strip()
                if p_line and not p_line.startswith("#"):
                    next_is_list = p_line.startswith("- ")
                    break
                peek += 1

            if isinstance(container, dict):
                if val_str == "" or (val_no_comment == "" and next_is_list):
                    new_container: Any = [] if next_is_list else {}
                    container[key] = new_container
                    stack.append((indent, new_container))
                else:
                    container[key] = val_no_comment

    return root


def parse_yaml_data(text: str) -> dict[str, Any] | None:
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else None
    except ImportError:
        return parse_subset_yaml(text)
    except Exception:
        return None


def run_config_tests(ctx: TestContext) -> None:
    agent_cfg_path = ctx.agent_dir / "config" / "agent.default.yaml"
    policy_cfg_path = ctx.agent_dir / "config" / "policy.default.yaml"

    for p in (agent_cfg_path, policy_cfg_path):
        if not p.is_file():
            ctx.fail("1.1.3 config file exists", f"Missing {p}")
            return

    agent_data = parse_yaml_data(agent_cfg_path.read_text(encoding="utf-8"))
    policy_data = parse_yaml_data(policy_cfg_path.read_text(encoding="utf-8"))

    if agent_data is None or policy_data is None:
        ctx.fail("1.1.3 YAML parsing", "Failed to parse default YAML templates")
        return
    ctx.ok("1.1.3 YAML parsing", "agent.default.yaml & policy.default.yaml parsed")

    required_sections = ["agent", "ipc", "collector", "storage", "wasm_engine"]
    missing_sections = [s for s in required_sections if s not in agent_data]
    if missing_sections:
        ctx.fail("1.1.3 agent config sections", f"Missing {missing_sections}")
    else:
        ctx.ok("1.1.3 agent config sections", ", ".join(required_sections))

    collector_mode = agent_data.get("collector", {}).get("mode")
    enforcement_mode = policy_data.get("enforcement_mode")
    if collector_mode == "passive_observation" and enforcement_mode == "audit_only":
        ctx.ok("1.1.3 passive & audit defaults", "passive_observation / audit_only")
    else:
        ctx.fail(
            "1.1.3 passive & audit defaults",
            f"Got collector.mode={collector_mode!r}, enforcement_mode={enforcement_mode!r}",
        )

    storage_driver = agent_data.get("storage", {}).get("driver")
    if storage_driver in {"sqlite", "badger"}:
        ctx.ok("1.1.3 storage driver allowlist", f"driver={storage_driver!r}")
    else:
        ctx.fail("1.1.3 storage driver allowlist", f"Invalid driver={storage_driver!r}")

    ipc_cfg = agent_data.get("ipc", {})
    wasm_cfg = agent_data.get("wasm_engine", {})
    bounds_ok = (
        isinstance(ipc_cfg.get("max_frame_bytes"), int) and ipc_cfg["max_frame_bytes"] > 0
        and isinstance(wasm_cfg.get("max_memory_pages"), int) and wasm_cfg["max_memory_pages"] > 0
        and isinstance(wasm_cfg.get("execution_timeout_ms"), int) and wasm_cfg["execution_timeout_ms"] > 0
    )
    if bounds_ok:
        ctx.ok("1.1.3 positive resource bounds", "max_frame_bytes, max_memory_pages, execution_timeout_ms > 0")
    else:
        ctx.fail("1.1.3 positive resource bounds", "One or more numeric limits <= 0 or non-integer")

    rules = policy_data.get("enabled_rule_modules", [])
    wasm_files = [r.get("wasm_file", "") for r in rules if isinstance(r, dict)]
    has_empty = any(not wf or not str(wf).strip() for wf in wasm_files)
    has_dupes = len(wasm_files) != len(set(wasm_files))
    if rules and not has_empty and not has_dupes:
        ctx.ok("1.1.3 rule module list", f"{len(wasm_files)} unique non-empty .wasm entries")
    else:
        ctx.fail("1.1.3 rule module list", f"Invalid rule modules: {wasm_files}")

    git = shutil.which("git")
    if git and (ctx.root / ".git").exists():
        rc, _, _ = ctx.run_cmd([git, "check-ignore", "-q", "config/local.yaml"], cwd=ctx.root)
        if rc == 0:
            ctx.ok("1.1.3 git check-ignore config/local.yaml", "Ignored by Git")
        else:
            ctx.fail("1.1.3 git check-ignore config/local.yaml", f"Expected exit 0, got {rc}")
    else:
        ctx.skip("1.1.3 git check-ignore", "git not available or .git missing")