from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .common import TestContext, UINT32_MAX, UINT64_MAX


def validate_record_against_schema(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["Record must be an object"]

    for req in schema.get("required", []):
        if req not in record:
            errors.append(f"Missing required top-level field: {req}")

    if "event_id" in record and not isinstance(record["event_id"], str):
        errors.append("event_id must be a string")

    if "timestamp_unix_ns" in record:
        ts = record["timestamp_unix_ns"]
        if isinstance(ts, bool) or not isinstance(ts, int) or ts < 0 or ts > UINT64_MAX:
            errors.append("timestamp_unix_ns must be a non-negative uint64 integer")

    if "host_id" in record and not isinstance(record["host_id"], str):
        errors.append("host_id must be a string")

    event_type = record.get("event_type")
    allowed_types = (
        schema.get("properties", {})
        .get("event_type", {})
        .get("enum", ["ProcessEvent", "FileEvent", "RegistryEvent"])
    )
    if event_type not in allowed_types:
        errors.append(f"Invalid event_type: {event_type!r}")

    payload = record.get("payload")
    if not isinstance(payload, dict):
        errors.append("payload must be an object")
        return errors

    if event_type == "ProcessEvent":
        for req in ("action", "pid", "ppid", "image_path"):
            if req not in payload:
                errors.append(f"ProcessEvent missing {req}")
        if payload.get("action") not in {"CREATED", "TERMINATED"}:
            errors.append(f"Invalid ProcessEvent.action: {payload.get('action')!r}")
        for pid_field in ("pid", "ppid"):
            if pid_field in payload:
                val = payload[pid_field]
                if isinstance(val, bool) or not isinstance(val, int) or val < 0 or val > UINT32_MAX:
                    errors.append(f"ProcessEvent.{pid_field} out of uint32 range")
        if "image_path" in payload and not isinstance(payload["image_path"], str):
            errors.append("ProcessEvent.image_path must be a string")

    elif event_type == "FileEvent":
        for req in ("action", "pid", "file_path"):
            if req not in payload:
                errors.append(f"FileEvent missing {req}")
        if payload.get("action") not in {"CREATED", "MODIFIED", "DELETED", "RENAMED"}:
            errors.append(f"Invalid FileEvent.action: {payload.get('action')!r}")
        if "pid" in payload:
            val = payload["pid"]
            if isinstance(val, bool) or not isinstance(val, int) or val < 0 or val > UINT32_MAX:
                errors.append("FileEvent.pid out of uint32 range")
        if "file_path" in payload and not isinstance(payload["file_path"], str):
            errors.append("FileEvent.file_path must be a string")

    elif event_type == "RegistryEvent":
        for req in ("action", "pid", "key_path"):
            if req not in payload:
                errors.append(f"RegistryEvent missing {req}")
        if payload.get("action") not in {"KEY_CREATED", "VALUE_SET", "KEY_DELETED", "VALUE_DELETED"}:
            errors.append(f"Invalid RegistryEvent.action: {payload.get('action')!r}")
        if "pid" in payload:
            val = payload["pid"]
            if isinstance(val, bool) or not isinstance(val, int) or val < 0 or val > UINT32_MAX:
                errors.append("RegistryEvent.pid out of uint32 range")
        if "key_path" in payload and not isinstance(payload["key_path"], str):
            errors.append("RegistryEvent.key_path must be a string")

    return errors


def run_schema_tests(ctx: TestContext) -> None:
    proto_path = ctx.agent_dir / "shared" / "telemetry.proto"
    json_schema_path = ctx.agent_dir / "shared" / "schema_contract.json"

    if not proto_path.is_file():
        ctx.fail("1.1.2 telemetry.proto exists", f"Missing {proto_path}")
        return
    if not json_schema_path.is_file():
        ctx.fail("1.1.2 schema_contract.json exists", f"Missing {json_schema_path}")
        return

    proto_text = proto_path.read_text(encoding="utf-8")
    try:
        schema = json.loads(json_schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        ctx.fail("1.1.2 JSON schema parse", f"Invalid JSON: {exc}")
        return

    expected_messages = ["TelemetryRecord", "ProcessEvent", "FileEvent", "RegistryEvent"]
    missing_msgs = [m for m in expected_messages if f"message {m}" not in proto_text]
    expected_oneof_fields = ["process_event", "file_event", "registry_event"]
    missing_oneofs = [f for f in expected_oneof_fields if f not in proto_text]

    if missing_msgs or missing_oneofs:
        ctx.fail(
            "1.1.2 Protobuf structure",
            f"Missing messages={missing_msgs}, oneof fields={missing_oneofs}",
        )
    else:
        ctx.ok("1.1.2 Protobuf structure", "messages & oneof variants present")

    protoc = shutil.which("protoc")
    if protoc:
        with tempfile.TemporaryDirectory(prefix="e6a1_proto_") as tmpdir:
            desc_out = Path(tmpdir) / "telemetry.pb"
            rc, _, err = ctx.run_cmd(
                [
                    protoc,
                    f"--proto_path={proto_path.parent}",
                    f"--descriptor_set_out={desc_out}",
                    proto_path.name,
                ],
                cwd=proto_path.parent,
            )
            if rc == 0:
                ctx.ok("1.1.2 protoc validation", "Compiled descriptor cleanly")
            else:
                ctx.fail("1.1.2 protoc validation", err.strip() or f"exit {rc}")
    else:
        ctx.skip("1.1.2 protoc validation", "protoc not found on PATH")

    required_top = set(schema.get("required", []))
    if {"event_id", "timestamp_unix_ns", "event_type", "payload"}.issubset(required_top):
        ctx.ok("1.1.2 JSON schema required fields", "event_id, timestamp_unix_ns, event_type, payload")
    else:
        ctx.fail("1.1.2 JSON schema required fields", f"Found {sorted(required_top)}")

    valid_fixtures: list[tuple[str, dict[str, Any]]] = [
        (
            "ProcessEvent CREATED",
            {
                "event_id": "evt-proc-001",
                "timestamp_unix_ns": 1732390000000000000,
                "host_id": "host-win-01",
                "event_type": "ProcessEvent",
                "payload": {
                    "action": "CREATED",
                    "pid": 4242,
                    "ppid": 1004,
                    "image_path": "C:\\Windows\\System32\\cmd.exe",
                    "command_line": "cmd.exe /c whoami",
                    "user_sid": "S-1-5-18",
                    "sha256_hash": "a" * 64,
                },
            },
        ),
        (
            "ProcessEvent TERMINATED (boundary pid=0, uint64 max timestamp)",
            {
                "event_id": "evt-proc-002",
                "timestamp_unix_ns": UINT64_MAX,
                "host_id": "host-win-01",
                "event_type": "ProcessEvent",
                "payload": {
                    "action": "TERMINATED",
                    "pid": 0,
                    "ppid": 0,
                    "image_path": "System Idle Process",
                },
            },
        ),
        (
            "FileEvent RENAMED",
            {
                "event_id": "evt-file-001",
                "timestamp_unix_ns": 1732390000000000100,
                "host_id": "host-win-01",
                "event_type": "FileEvent",
                "payload": {
                    "action": "RENAMED",
                    "pid": 5120,
                    "file_path": "C:\\Temp\\payload.exe",
                    "previous_path": "C:\\Temp\\payload.tmp",
                    "file_size_bytes": 4096,
                },
            },
        ),
        (
            "RegistryEvent VALUE_SET",
            {
                "event_id": "evt-reg-001",
                "timestamp_unix_ns": 1732390000000000200,
                "host_id": "host-win-01",
                "event_type": "RegistryEvent",
                "payload": {
                    "action": "VALUE_SET",
                    "pid": 5120,
                    "key_path": "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                    "value_name": "Updater",
                    "value_data_preview": "C:\\Temp\\payload.exe",
                },
            },
        ),
    ]

    for label, sample in valid_fixtures:
        errs = validate_record_against_schema(sample, schema)
        if not errs:
            ctx.ok(f"1.1.2 valid fixture [{label}]")
        else:
            ctx.fail(f"1.1.2 valid fixture [{label}]", "; ".join(errs))

    negative_fixtures: list[tuple[str, dict[str, Any]]] = [
        (
            "missing event_id",
            {
                "timestamp_unix_ns": 100,
                "event_type": "ProcessEvent",
                "payload": {"action": "CREATED", "pid": 10, "ppid": 4, "image_path": "a.exe"},
            },
        ),
        (
            "negative timestamp_unix_ns",
            {
                "event_id": "evt-neg-ts",
                "timestamp_unix_ns": -1,
                "event_type": "ProcessEvent",
                "payload": {"action": "CREATED", "pid": 10, "ppid": 4, "image_path": "a.exe"},
            },
        ),
        (
            "unknown event_type",
            {
                "event_id": "evt-bad-type",
                "timestamp_unix_ns": 100,
                "event_type": "NetworkEvent",
                "payload": {"action": "CREATED", "pid": 10, "ppid": 4, "image_path": "a.exe"},
            },
        ),
        (
            "mismatched FileEvent payload with RegistryEvent type",
            {
                "event_id": "evt-mismatch",
                "timestamp_unix_ns": 100,
                "event_type": "RegistryEvent",
                "payload": {"action": "CREATED", "pid": 10, "file_path": "C:\\a.txt"},
            },
        ),
    ]

    for label, bad_sample in negative_fixtures:
        errs = validate_record_against_schema(bad_sample, schema)
        if errs:
            ctx.ok(f"1.1.2 negative case [{label}]", f"Rejected: {errs[0]}")
        else:
            ctx.fail(f"1.1.2 negative case [{label}]", "Expected validation error, but passed")
