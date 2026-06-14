---
icon: lucide/users
---

# Per-team telemetry routing

Each DevOps/SRE team can own its **own** slice of the agent's telemetry— its own
Elasticsearch indices, dashboards, and access control— rather than sharing one
`claude-agent-*` index. The addon lives at
[`addons/team-routing/`](https://github.com/bigg01/claude-ci-agent/tree/main/addons/team-routing).

## The model— who picks the index

A common assumption is that the *dashboard* or the *OTLP receiver* sends data to a
team's index. Neither does:

- The **OTLP receiver** ingests everything; it has no notion of destination.
- The **dashboard** only reads.
- **The exporter writes the index**, from a **routing key the run carries**
  (`team.name`, set via `OTEL_TEAM`). RBAC and Kibana data views are downstream
  consumers of those indices.

So a run lands in its team's index because **the run tags itself** and **the
collector's exporter honours that tag**.

## Topology A— a collector per team (recommended)

Each team deploys its **own** OTel Collector, pinned to its `OTEL_TEAM`. That
collector forces every record into `claude-agent-<team>-*`, so a mistagged run
can't cross tenants— isolation is by *deployment*, not by trust. A team can even
point at its own Elasticsearch cluster, egress, and retention.

```text
Team A agents ─▶ otel-collector-team-a ─▶ claude-agent-team-a-*  ─▶ Kibana (Team A view + role)
Team B agents ─▶ otel-collector-team-b ─▶ claude-agent-team-b-*  ─▶ Kibana (Team B view + role)
```

Run one collector per team from `addons/team-routing/collector-config.team.yaml`,
each started with its own `OTEL_TEAM` (e.g. `sre-payments`, `sre-platform`).

Point that team's agents at their collector:

```
OTEL_EXPORTER_OTLP_ENDPOINT = http://otel-collector-sre-payments.observability:4318
```

## Topology B— one shared collector, routed by attribute

Prefer a single collector? [`collector-config.routing.yaml`](https://github.com/bigg01/claude-ci-agent/blob/main/addons/team-routing/collector-config.routing.yaml)
reads `team.name` off each run and dynamically writes to
`logs-claude.agent-<team>`. Adding a team needs **no** collector change— just a new
`OTEL_TEAM` on that pipeline.

| | A— collector per team | B— shared, routed |
| --- | --- | --- |
| Isolation | Strong (separate deployment) | Logical (one collector) |
| Add a team | Deploy a collector | Set `OTEL_TEAM` |
| Own cluster / egress / retention | Yes | No |
| Best for | Autonomous teams, strict tenancy | One central platform team |

## Tagging the run

Both rely on the run declaring its team— set `OTEL_TEAM` (it flows into
`OTEL_RESOURCE_ATTRIBUTES` as `team.name=<team>`):

=== "GitLab CI"

    Set the `OTEL_TEAM` CI/CD variable (project or group). It is already folded
    into `OTEL_RESOURCE_ATTRIBUTES` by [`.gitlab-ci.yml`](https://github.com/bigg01/claude-ci-agent/blob/main/.gitlab-ci.yml).

=== "GitHub Actions"

    Set the `OTEL_TEAM` repository/org **variable**; the workflow appends
    `team.name` to `OTEL_RESOURCE_ATTRIBUTES`.

Untagged runs fall back to the `default` team/index.

## Per-team access control

Scope an Elasticsearch role to the team's index pattern so members see only their
own data:

```jsonc
// PUT _security/role/claude-agent-sre-payments
{
  "indices": [
    { "names": ["claude-agent-sre-payments-*"], "privileges": ["read", "view_index_metadata"] }
  ]
}
```

Then create a matching Kibana data view (`claude-agent-sre-payments-*`)— the
project's [`local/kibana-setup.sh`](https://github.com/bigg01/claude-ci-agent/blob/main/local/kibana-setup.sh)
shows the API call; pass the team pattern. See [Observability](observability.md)
for the panels.
