#!/usr/bin/env bash
#
# Import the Claude CI Agent dashboard (and its data views) into a running Kibana.
# The saved objects live in local/kibana-dashboard.ndjson — regenerate them with
# `python3 local/make_dashboard.py`. Run this after `make stack-up` and at least
# one telemetry event (e.g. `make ci-local KEEP_UP=1`) so the indices exist.
#
# Usage: local/kibana-setup.sh
# Env:   KIBANA_URL (default: http://localhost:5601)

set -euo pipefail

KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NDJSON="$HERE/kibana-dashboard.ndjson"

[ -f "$NDJSON" ] || { echo "missing $NDJSON — run: python3 local/make_dashboard.py" >&2; exit 1; }

echo "▶ Waiting for Kibana at $KIBANA_URL"
until curl -fs "$KIBANA_URL/api/status" >/dev/null 2>&1; do sleep 3; done

echo "▶ Importing dashboard + data views"
result="$(curl -fsS -X POST "$KIBANA_URL/api/saved_objects/_import?overwrite=true" \
  -H 'kbn-xsrf: true' --form "file=@$NDJSON")"
echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  imported {d['successCount']} objects, success={d['success']}\")"

echo
echo "Open the dashboard:"
echo "  $KIBANA_URL/app/dashboards#/view/claude-agent-overview"
echo "Explore raw logs in Discover with the 'claude-agent-logs*' data view."
