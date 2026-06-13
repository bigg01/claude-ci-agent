#!/usr/bin/env python3
"""Push the cost of a Claude CI run to the OTel Collector as an OTLP metric.

Claude Code already emits a periodic ``claude_code.cost.usage`` metric, but the
metrics exporter only flushes on ``OTEL_METRIC_EXPORT_INTERVAL`` (60s by
default)— a short CI job exits first and the datapoint is lost. This helper
reads the authoritative ``total_cost_usd`` from ``claude -p --output-format
json`` and POSTs it to the collector immediately, enriched with CI metadata so
each run is attributable in Elastic.

Usage— ``python3 otel/emit_cost.py <result.json>`` (or ``-`` for stdin).

Best-effort by design— any transport or parse failure is logged to stderr and
the process still exits 0, so emitting cost can never fail the pipeline. Wrap
with ``|| true`` as well if you want belt-and-braces.

Standard library only (urllib)— no third-party dependencies (CLAUDE.MD §Coding
Standards: dependency minimization).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request


def _log(message: str) -> None:
    """Emit a diagnostic to stderr— never to stdout, which carries the result."""
    print(f"[emit_cost] {message}", file=sys.stderr)


def _read_result(path: str) -> dict:
    """Load the Claude JSON result from a file path or stdin (``-``)."""
    raw = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    return json.loads(raw)


def _ci_metadata() -> dict[str, str]:
    """Collect CI context, detecting GitLab vs GitHub from the environment.

    Returns OTLP-friendly key=value strings— empty values are dropped by the
    caller so we never ship blank attributes.
    """
    env = os.environ
    if env.get("GITLAB_CI") == "true":
        return {
            "ci.system": "gitlab",
            "ci.pipeline.id": env.get("CI_PIPELINE_ID", ""),
            "ci.job.id": env.get("CI_JOB_ID", ""),
            "ci.job.name": env.get("CI_JOB_NAME", ""),
            "ci.event": env.get("CI_MERGE_REQUEST_IID", ""),
            "vcs.repository": env.get("CI_PROJECT_PATH", ""),
            "vcs.ref": env.get("CI_COMMIT_REF_NAME", ""),
            "vcs.revision": env.get("CI_COMMIT_SHA", ""),
        }
    if env.get("GITHUB_ACTIONS") == "true":
        return {
            "ci.system": "github",
            "ci.pipeline.id": env.get("GITHUB_RUN_ID", ""),
            "ci.job.id": env.get("GITHUB_JOB", ""),
            "ci.job.name": env.get("GITHUB_WORKFLOW", ""),
            "ci.event": env.get("PR_NUMBER", ""),
            "vcs.repository": env.get("GITHUB_REPOSITORY", ""),
            "vcs.ref": env.get("GITHUB_REF_NAME", ""),
            "vcs.revision": env.get("GITHUB_SHA", ""),
        }
    return {"ci.system": "unknown"}


def _attr(key: str, value) -> dict:
    """Build a single OTLP KeyValue, picking the right value type."""
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": str(value)}}
    if isinstance(value, float):
        return {"key": key, "value": {"doubleValue": value}}
    return {"key": key, "value": {"stringValue": str(value)}}


def _endpoint() -> str:
    """Resolve the OTLP/HTTP metrics endpoint from the standard OTel env vars."""
    explicit = os.environ.get("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
    if explicit:
        return explicit
    base = os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"
    ).rstrip("/")
    return f"{base}/v1/metrics"


def _build_payload(result: dict) -> dict:
    """Assemble the OTLP metrics request body from a Claude result object."""
    now_nano = str(time.time_ns())

    # Common attributes attached to every datapoint— CI context plus the run's
    # own identifiers. Blank values are skipped so dashboards stay clean.
    attrs = {k: v for k, v in _ci_metadata().items() if v}
    attrs["claude.personality"] = os.environ.get("CLAUDE_PERSONALITY", "unknown")
    attrs["claude.model"] = os.environ.get("CLAUDE_MODEL", "")
    for key, src in (
        ("claude.session.id", "session_id"),
        ("claude.num_turns", "num_turns"),
        ("claude.is_error", "is_error"),
    ):
        if src in result and result[src] is not None:
            attrs[key] = result[src]
    attrs = {k: v for k, v in attrs.items() if v != ""}
    dp_attrs = [_attr(k, v) for k, v in attrs.items()]

    metrics = []

    cost = result.get("total_cost_usd")
    if cost is not None:
        metrics.append(
            {
                "name": "cicd.claude.run.cost_usd",
                "description": "Authoritative cost of a single Claude CI run (client-side estimate).",
                "unit": "USD",
                "gauge": {
                    "dataPoints": [
                        {
                            "asDouble": float(cost),
                            "timeUnixNano": now_nano,
                            "attributes": dp_attrs,
                        }
                    ]
                },
            }
        )

    duration = result.get("duration_ms")
    if duration is not None:
        metrics.append(
            {
                "name": "cicd.claude.run.duration_ms",
                "description": "Wall-clock duration of the Claude CI run.",
                "unit": "ms",
                "gauge": {
                    "dataPoints": [
                        {
                            "asInt": str(int(duration)),
                            "timeUnixNano": now_nano,
                            "attributes": dp_attrs,
                        }
                    ]
                },
            }
        )

    # Token usage broken out by kind via a ``type`` attribute, mirroring the
    # built-in claude_code.token.usage metric.
    usage = result.get("usage") or {}
    token_kinds = {
        "input": usage.get("input_tokens"),
        "output": usage.get("output_tokens"),
        "cacheRead": usage.get("cache_read_input_tokens"),
        "cacheCreation": usage.get("cache_creation_input_tokens"),
    }
    token_points = [
        {
            "asInt": str(int(count)),
            "timeUnixNano": now_nano,
            "attributes": dp_attrs + [_attr("type", kind)],
        }
        for kind, count in token_kinds.items()
        if count is not None
    ]
    if token_points:
        metrics.append(
            {
                "name": "cicd.claude.run.tokens",
                "description": "Token usage for the Claude CI run, by type.",
                "unit": "tokens",
                "gauge": {"dataPoints": token_points},
            }
        )

    return {
        "resourceMetrics": [
            {
                "resource": {
                    "attributes": [_attr("service.name", "claude-ci-agent")]
                },
                "scopeMetrics": [
                    {
                        "scope": {"name": "claude-ci-agent.cost"},
                        "metrics": metrics,
                    }
                ],
            }
        ]
    }


def _post(url: str, payload: dict) -> None:
    """POST the OTLP/JSON metrics payload to the collector."""
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status >= 300:
            raise urllib.error.HTTPError(
                url, response.status, "unexpected status", response.headers, None
            )


def _total_tokens(result: dict) -> int | None:
    """Sum the usage token kinds, or None if the result carries no usage."""
    usage = result.get("usage") or {}
    counts = [
        usage.get(k)
        for k in (
            "input_tokens",
            "output_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
        )
    ]
    present = [int(c) for c in counts if c is not None]
    return sum(present) if present else None


def _cost_summary(result: dict) -> str | None:
    """One human-readable line: what this run cost in Anthropic API usage.

    Returns None when the result carries no cost, so callers can stay quiet.
    """
    cost = result.get("total_cost_usd")
    if cost is None:
        return None
    parts = [f"this run cost ${float(cost):.4f} in Anthropic API usage"]
    model = os.environ.get("CLAUDE_MODEL")
    if model:
        parts.append(model)
    turns = result.get("num_turns")
    if turns is not None:
        parts.append(f"{turns} turns")
    tokens = _total_tokens(result)
    if tokens is not None:
        parts.append(f"{tokens:,} tokens")
    duration = result.get("duration_ms")
    if duration is not None:
        parts.append(f"{float(duration) / 1000:.1f}s")
    return " · ".join(parts)


def _write_step_summary(result: dict) -> None:
    """Append a cost table to the GitHub Actions run summary, if running there."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    cost = result.get("total_cost_usd")
    if not path or cost is None:
        return
    tokens = _total_tokens(result)
    rows = [f"| **Anthropic cost** | **${float(cost):.4f}** |"]
    if os.environ.get("CLAUDE_MODEL"):
        rows.append(f"| Model | {os.environ['CLAUDE_MODEL']} |")
    if result.get("num_turns") is not None:
        rows.append(f"| Turns | {result['num_turns']} |")
    if tokens is not None:
        rows.append(f"| Tokens | {tokens:,} |")
    if result.get("duration_ms") is not None:
        rows.append(f"| Duration | {float(result['duration_ms']) / 1000:.1f}s |")
    table = "### 💰 Claude run cost\n\n| Metric | Value |\n| --- | --- |\n" + "\n".join(rows) + "\n"
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(table)
    except OSError as error:  # best-effort — never fail the run on a summary write
        _log(f"could not write GitHub step summary— {error}")


def _report_cost(result: dict) -> None:
    """Surface the run's Anthropic cost to the operator (log + CI summary)."""
    summary = _cost_summary(result)
    if summary:
        _log(f"💰 {summary}")
        _write_step_summary(result)
    else:
        _log("no total_cost_usd in result— cost unknown for this run")


def main() -> int:
    if len(sys.argv) != 2:
        _log("usage: emit_cost.py <result.json|->")
        return 0  # never break the pipeline on a wiring mistake

    try:
        result = _read_result(sys.argv[1])
    except (OSError, ValueError) as error:
        _log(f"could not read Claude result— {error}")
        return 0

    # Always show the operator what the run cost — independent of whether the
    # OTel collector is reachable below.
    _report_cost(result)

    payload = _build_payload(result)
    if not payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]:
        _log("no cost/usage fields in result— nothing to emit")
        return 0

    url = _endpoint()
    try:
        _post(url, payload)
    except (urllib.error.URLError, OSError) as error:
        # Collector may be absent (e.g. GitLab job without a sidecar)— log and
        # move on rather than failing the run.
        _log(f"could not reach collector at {url}— {error}")
        return 0

    cost = result.get("total_cost_usd")
    _log(f"pushed cost ${cost} to {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
