"""Unit tests for otel/emit_cost.py — the OTLP cost/usage emitter."""

from __future__ import annotations

import json

import pytest


# --------------------------------------------------------------------------- #
# _attr — OTLP KeyValue type selection
# --------------------------------------------------------------------------- #

def test_attr_bool(emit_cost):
    assert emit_cost._attr("k", True) == {"key": "k", "value": {"boolValue": True}}


def test_attr_int_is_stringified(emit_cost):
    # bool is a subclass of int — make sure it is checked first.
    assert emit_cost._attr("k", 5) == {"key": "k", "value": {"intValue": "5"}}


def test_attr_float(emit_cost):
    assert emit_cost._attr("k", 1.5) == {"key": "k", "value": {"doubleValue": 1.5}}


def test_attr_str_fallback(emit_cost):
    assert emit_cost._attr("k", "v") == {"key": "k", "value": {"stringValue": "v"}}


# --------------------------------------------------------------------------- #
# _endpoint — resolving the OTLP/HTTP metrics URL
# --------------------------------------------------------------------------- #

def test_endpoint_default(emit_cost, clean_ci_env):
    assert emit_cost._endpoint() == "http://localhost:4318/v1/metrics"


def test_endpoint_from_base(emit_cost, clean_ci_env):
    clean_ci_env.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318/")
    assert emit_cost._endpoint() == "http://collector:4318/v1/metrics"


def test_endpoint_explicit_metrics_wins(emit_cost, clean_ci_env):
    clean_ci_env.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://base:4318")
    clean_ci_env.setenv(
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "http://explicit:4318/v1/metrics"
    )
    assert emit_cost._endpoint() == "http://explicit:4318/v1/metrics"


# --------------------------------------------------------------------------- #
# _ci_metadata — GitLab / GitHub / unknown detection
# --------------------------------------------------------------------------- #

def test_ci_metadata_gitlab(emit_cost, clean_ci_env):
    clean_ci_env.setenv("GITLAB_CI", "true")
    clean_ci_env.setenv("CI_PIPELINE_ID", "42")
    clean_ci_env.setenv("CI_PROJECT_PATH", "group/repo")
    meta = emit_cost._ci_metadata()
    assert meta["ci.system"] == "gitlab"
    assert meta["ci.pipeline.id"] == "42"
    assert meta["vcs.repository"] == "group/repo"


def test_ci_metadata_github(emit_cost, clean_ci_env):
    clean_ci_env.setenv("GITHUB_ACTIONS", "true")
    clean_ci_env.setenv("GITHUB_RUN_ID", "99")
    meta = emit_cost._ci_metadata()
    assert meta["ci.system"] == "github"
    assert meta["ci.pipeline.id"] == "99"


def test_ci_metadata_unknown(emit_cost, clean_ci_env):
    assert emit_cost._ci_metadata() == {"ci.system": "unknown"}


# --------------------------------------------------------------------------- #
# _build_payload — assembling the OTLP metrics body
# --------------------------------------------------------------------------- #

def _metrics(payload):
    return payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]


def _by_name(payload):
    return {m["name"]: m for m in _metrics(payload)}


def test_build_payload_cost_and_duration(emit_cost, clean_ci_env):
    payload = emit_cost._build_payload({"total_cost_usd": 0.42, "duration_ms": 1500})
    metrics = _by_name(payload)
    assert "cicd.claude.run.cost_usd" in metrics
    cost_dp = metrics["cicd.claude.run.cost_usd"]["gauge"]["dataPoints"][0]
    assert cost_dp["asDouble"] == 0.42
    dur_dp = metrics["cicd.claude.run.duration_ms"]["gauge"]["dataPoints"][0]
    assert dur_dp["asInt"] == "1500"


def test_build_payload_tokens_by_type(emit_cost, clean_ci_env):
    payload = emit_cost._build_payload(
        {"usage": {"input_tokens": 10, "output_tokens": 20}}
    )
    tokens = _by_name(payload)["cicd.claude.run.tokens"]
    points = tokens["gauge"]["dataPoints"]
    kinds = {
        attr["value"]["stringValue"]
        for p in points
        for attr in p["attributes"]
        if attr["key"] == "type"
    }
    assert kinds == {"input", "output"}


def test_build_payload_resource_service_name(emit_cost, clean_ci_env):
    payload = emit_cost._build_payload({"total_cost_usd": 1.0})
    res_attrs = payload["resourceMetrics"][0]["resource"]["attributes"]
    assert {"key": "service.name", "value": {"stringValue": "claude-ci-agent"}} in res_attrs


def test_build_payload_empty_when_no_cost_fields(emit_cost, clean_ci_env):
    payload = emit_cost._build_payload({"irrelevant": "value"})
    assert _metrics(payload) == []


def test_build_payload_drops_blank_attrs(emit_cost, clean_ci_env):
    # CLAUDE_MODEL is blank by default — it must not appear as an attribute.
    payload = emit_cost._build_payload({"total_cost_usd": 1.0})
    dp = _metrics(payload)[0]["gauge"]["dataPoints"][0]
    keys = {a["key"] for a in dp["attributes"]}
    assert "claude.model" not in keys


# --------------------------------------------------------------------------- #
# main — must never break the pipeline (always returns 0)
# --------------------------------------------------------------------------- #

def test_main_bad_args_returns_zero(emit_cost, monkeypatch):
    monkeypatch.setattr(emit_cost.sys, "argv", ["emit_cost.py"])  # missing arg
    assert emit_cost.main() == 0


def test_main_missing_file_returns_zero(emit_cost, monkeypatch):
    monkeypatch.setattr(emit_cost.sys, "argv", ["emit_cost.py", "/no/such/file.json"])
    assert emit_cost.main() == 0


def test_main_no_metrics_returns_zero(emit_cost, monkeypatch, tmp_path):
    result = tmp_path / "result.json"
    result.write_text(json.dumps({"nothing": "useful"}))
    monkeypatch.setattr(emit_cost.sys, "argv", ["emit_cost.py", str(result)])
    assert emit_cost.main() == 0


def test_main_posts_and_returns_zero(emit_cost, monkeypatch, tmp_path, clean_ci_env):
    result = tmp_path / "result.json"
    result.write_text(json.dumps({"total_cost_usd": 0.5}))
    posted = {}

    def fake_post(url, payload):
        posted["url"] = url
        posted["payload"] = payload

    monkeypatch.setattr(emit_cost, "_post", fake_post)
    monkeypatch.setattr(emit_cost.sys, "argv", ["emit_cost.py", str(result)])
    assert emit_cost.main() == 0
    assert posted["url"].endswith("/v1/metrics")
    assert _metrics(posted["payload"])[0]["name"] == "cicd.claude.run.cost_usd"


# --------------------------------------------------------------------------- #
# Cost reporting — surface the run's Anthropic dollar cost
# --------------------------------------------------------------------------- #

def test_total_tokens_sums_all_kinds(emit_cost):
    total = emit_cost._total_tokens(
        {"usage": {"input_tokens": 10, "output_tokens": 20, "cache_read_input_tokens": 5}}
    )
    assert total == 35


def test_total_tokens_none_without_usage(emit_cost):
    assert emit_cost._total_tokens({}) is None


def test_cost_summary_includes_dollar_amount(emit_cost, clean_ci_env):
    summary = emit_cost._cost_summary(
        {"total_cost_usd": 0.4231, "num_turns": 2, "usage": {"input_tokens": 100}}
    )
    assert "$0.4231" in summary
    assert "Anthropic API usage" in summary
    assert "2 turns" in summary
    assert "100 tokens" in summary


def test_cost_summary_none_when_no_cost(emit_cost, clean_ci_env):
    assert emit_cost._cost_summary({"num_turns": 1}) is None


def test_report_cost_logs_dollar_amount(emit_cost, clean_ci_env, capsys):
    emit_cost._report_cost({"total_cost_usd": 1.2345})
    err = capsys.readouterr().err
    assert "$1.2345" in err


def test_write_step_summary_appends_markdown(emit_cost, monkeypatch, tmp_path):
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
    emit_cost._write_step_summary({"total_cost_usd": 0.75, "num_turns": 3})
    content = summary_file.read_text()
    assert "Claude run cost" in content
    assert "$0.7500" in content
    assert "| Turns | 3 |" in content


def test_write_step_summary_noop_without_env(emit_cost, monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    # Must not raise when not running under GitHub Actions.
    emit_cost._write_step_summary({"total_cost_usd": 0.75})


def test_main_swallows_post_failure(emit_cost, monkeypatch, tmp_path, clean_ci_env):
    import urllib.error

    result = tmp_path / "result.json"
    result.write_text(json.dumps({"total_cost_usd": 0.5}))

    def boom(url, payload):
        raise urllib.error.URLError("collector down")

    monkeypatch.setattr(emit_cost, "_post", boom)
    monkeypatch.setattr(emit_cost.sys, "argv", ["emit_cost.py", str(result)])
    # Transport failure must not propagate — cost emission can never fail a run.
    assert emit_cost.main() == 0
