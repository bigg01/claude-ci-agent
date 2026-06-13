#!/usr/bin/env sh
# Render + apply a per-team OTel Collector (Deployment + Service + ConfigMap).
#
# Usage:
#   TEAM=sre-payments ./render.sh | kubectl apply -f -      # review then apply
#   TEAM=sre-payments APPLY=1 ./render.sh                   # apply directly
#
# Env:
#   TEAM             (required) team slug → claude-agent-<team>-* indices
#   NAMESPACE        target namespace (default: observability)
#   ES_ENDPOINT      Elasticsearch URL (default: http://elasticsearch:9200)
#   COLLECTOR_IMAGE  collector image (default: otel/opentelemetry-collector-contrib:latest)
#   APPLY            when set, pipe the manifests straight to `kubectl apply -f -`
set -eu

: "${TEAM:?set TEAM to the team slug, e.g. TEAM=sre-payments}"
NAMESPACE="${NAMESPACE:-observability}"
ES_ENDPOINT="${ES_ENDPOINT:-http://elasticsearch:9200}"
COLLECTOR_IMAGE="${COLLECTOR_IMAGE:-otel/opentelemetry-collector-contrib:latest}"
here="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

export TEAM NAMESPACE ES_ENDPOINT COLLECTOR_IMAGE

render() {
  # 1. ConfigMap holding the single-tenant collector config (team-agnostic
  #    content; OTEL_TEAM in the Deployment selects the index at runtime).
  kubectl create configmap "otel-collector-${TEAM}" \
    --namespace "${NAMESPACE}" \
    --from-file=config.yaml="${here}/../collector-config.team.yaml" \
    --dry-run=client -o yaml
  echo "---"
  # 2. Deployment + Service, with placeholders substituted.
  envsubst '${TEAM} ${NAMESPACE} ${ES_ENDPOINT} ${COLLECTOR_IMAGE}' \
    < "${here}/otel-collector.team.yaml"
}

if [ -n "${APPLY:-}" ]; then
  render | kubectl apply -f -
else
  render
fi
