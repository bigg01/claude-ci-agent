# Per-team telemetry routing addon (optional)

Give each DevOps/SRE team its **own** slice of the agent's telemetry— its own
Elasticsearch indices, its own dashboards, its own access control— instead of one
shared `claude-agent-*` index everyone reads.

## Correcting the mental model

> "The dashboard / the OTLP receiver should send to the team's index."

Not quite— and the distinction matters:

- The **OTLP receiver** ingests *everything* sent to it; it doesn't pick a
  destination.
- The **dashboard** only *reads*; it never decides where data is stored.
- **The exporter decides the index**, from a **routing key the run carries**
  (`team.name`, set via `OTEL_TEAM`). Per-team **RBAC** and **Kibana data views**
  are downstream *consumers* of those indices.

So the team is chosen at the source (the run tags itself) and honoured at the
exporter. Two topologies implement that:

## Topology A — a collector per team (recommended)

Each team deploys its **own** collector ([`collector-config.team.yaml`](collector-config.team.yaml)),
pinned to its `OTEL_TEAM`. The collector **forces** every record into
`claude-agent-<team>-*`, so a mistagged run cannot leak across tenants— isolation
is by *deployment*, not by trust. This also lets a team own its own egress, RBAC,
retention, and even a separate Elasticsearch cluster.

```text
Team A agents ─▶ otel-collector-team-a ─▶ claude-agent-team-a-*
Team B agents ─▶ otel-collector-team-b ─▶ claude-agent-team-b-*
```

Deploy one per team with [`k8s/render.sh`](k8s/render.sh):

```sh
TEAM=sre-payments  APPLY=1 ./k8s/render.sh        # otel-collector-sre-payments
TEAM=sre-platform  APPLY=1 ./k8s/render.sh        # otel-collector-sre-platform
```

Then point that team's agents at their collector:

```
OTEL_EXPORTER_OTLP_ENDPOINT = http://otel-collector-sre-payments.observability:4318
```

## Topology B — one shared collector, route by attribute

If you'd rather run a single collector, [`collector-config.routing.yaml`](collector-config.routing.yaml)
uses dynamic data-stream indexing: it reads `team.name` off each run and writes
to `logs-claude.agent-<team>` (adding a team needs **no** collector change— just a
new `OTEL_TEAM` on that pipeline). Use this when one platform team owns the
collector and tenants differ only by index + RBAC.

| | Topology A (per-team collector) | Topology B (shared, routed) |
| --- | --- | --- |
| Isolation | Strong— separate deployment per team | Logical— one collector, many indices |
| Add a team | Deploy a collector | Just set `OTEL_TEAM` |
| Own egress / cluster / retention | Yes | No (shared) |
| Best for | Autonomous teams, strict tenancy | Central platform team |

## Tagging the run

Both topologies rely on the run declaring its team. Set `OTEL_TEAM` (it flows into
`OTEL_RESOURCE_ATTRIBUTES` as `team.name=<team>`):

```
OTEL_TEAM = sre-payments
```

Untagged runs fall back to the `default` team/index.

## Per-team access control (Elasticsearch)

Scope a role to the team's index pattern so members see only their data:

```jsonc
// PUT _security/role/claude-agent-sre-payments
{
  "indices": [
    { "names": ["claude-agent-sre-payments-*"], "privileges": ["read", "view_index_metadata"] }
  ]
}
```

Create a matching Kibana data view per team (`claude-agent-sre-payments-*`)— the
project's `local/kibana-setup.sh` shows the API call; pass the team pattern.
