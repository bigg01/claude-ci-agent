#!/usr/bin/env bash
#
# Local CI test — exercises the full telemetry path on the Podman Compose stack:
#
#   agent → OTLP/HTTP → OTel Collector (secret scrub) → Elasticsearch → (Kibana)
#
# It does NOT need ANTHROPIC_API_KEY: instead of a real agent run it posts a
# synthetic OTLP log carrying a fake secret, then asserts the event lands in
# Elasticsearch with the secret redacted.
#
# Usage:
#   tests/ci-local.sh            # up → test → down
#   KEEP_UP=1 tests/ci-local.sh  # leave the stack running afterwards
#
# Env:
#   COMPOSE   compose command   (default: "podman compose")
#   ES_URL    Elasticsearch URL (default: http://localhost:9200)
#   OTLP_URL  collector OTLP/HTTP (default: http://localhost:4318)

set -euo pipefail

COMPOSE="${COMPOSE:-podman compose}"
ES_URL="${ES_URL:-http://localhost:9200}"
OTLP_URL="${OTLP_URL:-http://localhost:4318}"
MARKER="CI_LOCAL_PROBE_$$"
FAKE_SECRET="sk-ant-FAKE0123456789"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pass() { printf '\033[32m✓ %s\033[0m\n' "$1"; }
info() { printf '\033[36m▶ %s\033[0m\n' "$1"; }
fail() { printf '\033[31m✗ %s\033[0m\n' "$1" >&2; exit 1; }

cleanup() {
  if [ "${KEEP_UP:-0}" = "1" ]; then
    info "KEEP_UP=1 — leaving the stack running (kibana: http://localhost:5601)"
  else
    info "Tearing down the stack"
    $COMPOSE down -v >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

# Poll a command until it succeeds or times out. Args: <timeout-s> <desc> <cmd...>
wait_for() {
  local timeout="$1" desc="$2"; shift 2
  local deadline=$(( $(date +%s) + timeout ))
  until "$@" >/dev/null 2>&1; do
    [ "$(date +%s)" -ge "$deadline" ] && fail "timed out waiting for $desc (${timeout}s)"
    sleep 2
  done
  pass "$desc ready"
}

# ---------------------------------------------------------------------------
info "Bringing up Elasticsearch + OTel Collector"
$COMPOSE up -d elasticsearch otel-collector || fail "compose up failed"

wait_for 180 "Elasticsearch" curl -fs "$ES_URL/_cluster/health"
wait_for 60  "OTel Collector OTLP port" bash -c "curl -s -o /dev/null '$OTLP_URL/v1/logs'"

# ---------------------------------------------------------------------------
info "Posting a synthetic OTLP log (with a fake secret) to the collector"
NOW_NS="$(date +%s)000000000"
PAYLOAD=$(cat <<JSON
{
  "resourceLogs": [{
    "resource": {"attributes": [
      {"key": "service.name", "value": {"stringValue": "claude-agent"}},
      {"key": "ci.flavor",    "value": {"stringValue": "local"}}
    ]},
    "scopeLogs": [{
      "logRecords": [{
        "timeUnixNano": "$NOW_NS",
        "severityText": "INFO",
        "body": {"stringValue": "tool=Bash cmd='npm test' api_key=$FAKE_SECRET marker=$MARKER"}
      }]
    }]
  }]
}
JSON
)

code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$OTLP_URL/v1/logs" \
  -H 'Content-Type: application/json' -d "$PAYLOAD")
[ "$code" = "200" ] && pass "collector accepted the OTLP log (HTTP 200)" \
  || fail "collector rejected the OTLP log (HTTP $code)"

# ---------------------------------------------------------------------------
info "Verifying the event reached Elasticsearch — scrubbed"
HITS_JSON=""
deadline=$(( $(date +%s) + 60 ))
while :; do
  curl -fs -X POST "$ES_URL/claude-agent-logs/_refresh" >/dev/null 2>&1 || true
  HITS_JSON="$(curl -fs "$ES_URL/claude-agent-logs/_search?q=$MARKER&size=5" 2>/dev/null || true)"
  echo "$HITS_JSON" | grep -q "$MARKER" && break
  [ "$(date +%s)" -ge "$deadline" ] && fail "event with marker $MARKER never reached Elasticsearch"
  sleep 2
done
pass "event indexed in Elasticsearch (marker found)"

if echo "$HITS_JSON" | grep -q "$FAKE_SECRET"; then
  fail "SECRET LEAKED — raw key '$FAKE_SECRET' found in the stored document"
fi
pass "secret was scrubbed (raw key absent from the stored document)"

echo
pass "local CI test passed"
