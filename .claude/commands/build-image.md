---
description: Build the rootless Podman sandbox image and smoke-test it (toolchain, baked CI helpers, cost emitter).
argument-hint: "[image tag, default app-test]"
allowed-tools: Bash(podman:*), Bash(make:*), Read
---

Build the agent sandbox image from `Containerfile` and verify it's actually
usable in CI. Use the tag `$ARGUMENTS` if given, otherwise `app-test`.

## Build

Run `podman build -t <tag> -f Containerfile .` (equivalently `make build`). The
build itself runs `podman --version && node --version && claude --version` as a
smoke test, so a green build already proves the core toolchain.

## Smoke-test the built image

The GitLab component and GitHub workflow depend on more than `claude` — they need
`jq`/`curl` and the **baked CI helpers** at `/opt/claude-ci/`. Verify inside the
image (run as the default non-root UID):

```sh
podman run --rm --entrypoint /bin/sh <tag> -c '
  for t in jq curl python3 node claude git; do command -v "$t" >/dev/null || echo "MISSING: $t"; done
  ls /opt/claude-ci/emit_cost.py /opt/claude-ci/otel-collector-config.yaml /opt/claude-ci/fetch-secrets.sh
  printf "%s" "{\"total_cost_usd\":0.01,\"num_turns\":1}" > /tmp/r.json
  python3 /opt/claude-ci/emit_cost.py /tmp/r.json   # best-effort, must exit 0
  id
'
```

Optionally validate the OTel sidecar config the component mounts:

```sh
podman run --rm -e ELASTIC_OTLP_ENDPOINT=https://x.invalid:443 -e ELASTIC_OTLP_AUTHORIZATION=dummy \
  -v "$PWD/otel/otel-collector-config.yaml:/etc/otelcol/config.yaml:ro,Z" \
  docker.io/otel/opentelemetry-collector-contrib:latest validate --config /etc/otelcol/config.yaml
```

## Report

Confirm: build exit code, any MISSING tool, that all three helpers are present and
world-readable, that `emit_cost.py` exits 0, and the running UID (should be
`uid=1001 gid=0`). Call out anything that would break the component in CI.
