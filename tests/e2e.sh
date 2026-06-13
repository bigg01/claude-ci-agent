#!/usr/bin/env bash
#
# End-to-end test for the Claude CI agent — runs locally first, then unchanged in CI.
#
# Stages (each fails fast):
#   1. Validate configs   — Zensical docs build + GitLab component / TOML parse
#   2. Build image        — $CE build of the rootless sandbox (skip: SKIP_BUILD=1)
#   3. Toolchain smoke     — claude/node/$CE present inside the container
#   4. Live agent run     — real claude prompt, only if ANTHROPIC_API_KEY is set
#
# Usage:
#   tests/e2e.sh              # full run
#   SKIP_BUILD=1 tests/e2e.sh # skip the (slow) image build, reuse existing image
#
# Env:
#   IMAGE              container image tag        (default: app-test)
#   CONTAINERFILE      Containerfile path         (default: Containerfile)
#   ANTHROPIC_API_KEY  enables the live agent run (optional)

set -euo pipefail

IMAGE="${IMAGE:-app-test}"
CONTAINERFILE="${CONTAINERFILE:-Containerfile}"
CE="${CONTAINER_ENGINE:-podman}"

# Resolve repo root so the test works from any working directory.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pass() { printf '\033[32m✓ %s\033[0m\n' "$1"; }
info() { printf '\033[36m▶ %s\033[0m\n' "$1"; }
fail() { printf '\033[31m✗ %s\033[0m\n' "$1" >&2; exit 1; }

# ---------------------------------------------------------------------------
info "Stage 1/4 — validate configs"
# ---------------------------------------------------------------------------

uv run zensical build --clean >/dev/null 2>&1 \
  && pass "docs build (zensical)" \
  || fail "docs build failed — run 'uv run zensical build' to see why"

[ -f site/index.html ] || fail "docs build produced no site/index.html"
pass "docs output present"

uv run python - "$CONTAINERFILE" <<'PY' || fail "config validation failed"
import sys, tomllib, yaml

# zensical.toml must be valid TOML.
with open("zensical.toml", "rb") as fh:
    tomllib.load(fh)

# The GitLab component must be a valid two-document YAML (spec + job).
with open("templates/claude-agent.yml") as fh:
    docs = list(yaml.safe_load_all(fh))
assert len(docs) == 2, f"expected spec + job documents, got {len(docs)}"
spec, job = docs
assert "inputs" in spec.get("spec", {}), "component spec.inputs missing"
assert "prompt" in spec["spec"]["inputs"], "component is missing the 'prompt' input"
assert "claude-agent" in job, "component job 'claude-agent' missing"

# Kubernetes deploy manifests (AKS / OpenShift) must parse and be hardened.
# The manifest may hold several documents (e.g. ServiceAccount + Job).
with open("deploy/agent-job.yaml") as fh:
    agent_job = next(d for d in yaml.safe_load_all(fh) if d and d.get("kind") == "Job")
pod = agent_job["spec"]["template"]["spec"]
assert pod["securityContext"]["runAsNonRoot"] is True, "pod must be runAsNonRoot (AKS restricted PSS)"
container = pod["containers"][0]["securityContext"]
assert container["allowPrivilegeEscalation"] is False, "allowPrivilegeEscalation must be false"
assert container["capabilities"]["drop"] == ["ALL"], "container must drop ALL capabilities"

with open("deploy/networkpolicy.yaml") as fh:
    netpol = yaml.safe_load(fh)
assert netpol["kind"] == "NetworkPolicy", "networkpolicy.yaml is not a NetworkPolicy"
assert netpol["spec"]["ingress"] == [], "NetworkPolicy must deny all ingress"
print("ok")
PY
pass "zensical.toml + GitLab component + k8s manifests parse cleanly"

# ---------------------------------------------------------------------------
info "Stage 2/4 — build sandbox image"
# ---------------------------------------------------------------------------

if [ "${SKIP_BUILD:-0}" = "1" ]; then
  $CE image exists "$IMAGE" || fail "SKIP_BUILD=1 but image '$IMAGE' does not exist"
  pass "reusing existing image '$IMAGE' (SKIP_BUILD=1)"
else
  $CE build -t "$IMAGE" -f "$CONTAINERFILE" . \
    && pass "image '$IMAGE' built" \
    || fail "$CE build failed"
fi

# ---------------------------------------------------------------------------
info "Stage 3/4 — toolchain smoke test (inside container)"
# ---------------------------------------------------------------------------

# Run as the image default user. OpenShift injects an arbitrary high non-root UID
# at runtime; we don't force it here because local rootless engines can't map a
# UID outside the host subuid range (the build-time smoke test already exercises
# the group-writable HOME/npm prefix that makes arbitrary UIDs work).
run() { $CE run --rm "$IMAGE" "$@"; }

run claude --version >/dev/null && pass "claude CLI present" || fail "claude CLI missing in image"
run node --version   >/dev/null && pass "node present"        || fail "node missing in image"
run $CE --version >/dev/null && pass "$CE present"      || fail "$CE missing in image"

# ---------------------------------------------------------------------------
info "Stage 4/4 — live agent run"
# ---------------------------------------------------------------------------

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  OUT="$($CE run --rm \
      -e ANTHROPIC_API_KEY \
      -e CLAUDE_CODE_ENABLE_TELEMETRY=1 \
      "$IMAGE" \
      claude --dangerously-skip-permissions -p 'Reply with exactly: E2E_OK' 2>&1)" \
    || fail "live agent run errored: $OUT"
  printf '%s' "$OUT" | grep -q "E2E_OK" \
    && pass "live agent responded as expected" \
    || fail "live agent output did not contain E2E_OK: $OUT"
else
  printf '\033[33m• skipped — set ANTHROPIC_API_KEY to enable the live agent run\033[0m\n'
fi

echo
pass "e2e passed"
