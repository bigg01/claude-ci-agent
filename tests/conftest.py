"""Shared pytest fixtures for the Claude CI agent test suite."""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load_module(name: str, relpath: str):
    """Load a standalone script (not a package) by file path."""
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def emit_cost():
    """The otel/emit_cost.py module, loaded fresh for each test."""
    return _load_module("emit_cost", "otel/emit_cost.py")


@pytest.fixture
def clean_ci_env(monkeypatch):
    """Strip CI-detection env vars so tests start from a known-empty state."""
    for var in (
        "GITLAB_CI",
        "GITHUB_ACTIONS",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
        "CLAUDE_PERSONALITY",
        "CLAUDE_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch
