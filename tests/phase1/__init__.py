"""Modular Phase 1 test suite for E6A1."""

from .common import TestContext
from .test_schemas import run_schema_tests
from .test_configs import run_config_tests
from .test_build_isolation import run_build_isolation_tests

__all__ = [
    "TestContext",
    "run_schema_tests",
    "run_config_tests",
    "run_build_isolation_tests",
]
