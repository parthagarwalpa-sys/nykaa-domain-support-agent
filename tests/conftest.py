"""Pytest configuration for Step 1B smoke tests."""

from __future__ import annotations

import os


def pytest_configure() -> None:
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
