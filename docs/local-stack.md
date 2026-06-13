---
icon: lucide/container
---

# Local stack (Podman Compose)

Run the whole observability pipeline on your machine— **Elasticsearch + Kibana +
OTel Collector + the agent**— with Podman Compose. This lets you build, run the
local CI test, and see telemetry land in a real Kibana, without a cluster.

```
agent ──OTLP/HTTP──▶ OTel Collector ──(secret scrub)──▶ Elasticsearch ──▶ Kibana
```

!!! warning "Elasticsearch host requirement"

    Elasticsearch needs `vm.max_map_count >= 262144` on the host:

    ```bash
    sudo sysctl -w vm.max_map_count=262144
    ```

## Services

Defined in [`compose.yaml`](https://github.com/bigg01/claude-ci-agent/blob/main/compose.yaml):

| Service | Image | Port | Role |
| --- | --- | --- | --- |
| `elasticsearch` | `elasticsearch:8.15.0` | 9200 | Stores the audit trail |
| `kibana` | `kibana:8.15.0` | 5601 | Dashboards / Discover |
| `otel-collector` | `otel-collector-contrib` | 4317/4318 | Receives OTLP, **scrubs secrets**, exports to ES |
| `agent` *(profile `agent`)* | `app-test` (built locally) | — | The agent itself; needs `ANTHROPIC_API_KEY` |

The collector uses [`otel/collector-config.local.yaml`](https://github.com/bigg01/claude-ci-agent/blob/main/otel/collector-config.local.yaml)—
the same credential scrubbing as production, but exporting to the local
Elasticsearch instead of Elastic Cloud's OTLP intake.

## Commands

```bash
make compose-build    # build the agent image via compose
make stack-up         # start Elasticsearch + Kibana + OTel Collector
make ci-local         # bring the stack up and run the telemetry e2e test
make dashboard        # create Kibana data views for claude-agent-*
make stack-logs       # tail logs
make stack-down       # stop everything and remove volumes
```

## Local CI test

[`tests/ci-local.sh`](https://github.com/bigg01/claude-ci-agent/blob/main/tests/ci-local.sh)
(`make ci-local`) exercises the full telemetry path **without an API key**: instead
of a real agent run it posts a synthetic OTLP log carrying a *fake* secret, then
asserts the event:

1. is accepted by the collector (HTTP 200),
2. lands in the `claude-agent-logs` index in Elasticsearch, and
3. has the secret **redacted** (the raw key must be absent from the stored document).

Step 3 is the important one— it proves the scrubbing in the collector works
end-to-end, not just in config. Use `KEEP_UP=1 make ci-local` to leave the stack
running afterwards so you can open Kibana.

## Running the real agent

With a key set, run the agent service against the collector:

```bash
ANTHROPIC_API_KEY=… podman-compose --profile agent up agent
```

Then open [http://localhost:5601](http://localhost:5601), run `make dashboard`, and
explore in Discover. The target layout is the [Observability](observability.md) sketch.
