---
icon: lucide/rocket
---

<p align="center">
  <img src="assets/banner.svg" alt="Claude CI Agent" width="760">
</p>

# Claude CI Agent

An autonomous engineering teammate that executes inside a **rootless, unprivileged
Podman sandbox**. Every action it takes is captured, scrubbed for secrets, and
streamed to Elastic through an OpenTelemetry (OTel) Collector sidecar.

## Start here

There are two ways to run the agent. Choose your path:

<div class="grid cards" markdown>

-   :material-source-branch:{ .lg .middle } **Run it in CI**

    ---

    Wire the agent into **GitLab CI** or **GitHub Actions**— an *advisor* that
    reviews merge/pull requests, or an *agent* that applies a fix and opens a new
    branch. Triggered by pipelines and `@claude` comments.

    [:octicons-arrow-right-24: CI Versions](ci-versions.md) ·
    [Wire it into CI](getting-started.md#step-6-wire-it-into-ci)

</div>

Either way it is the same rootless, OTel-audited sandbox— in CI it detects
**GitLab CI** vs **GitHub Actions** automatically.

## Quick links

- :material-sitemap: **[Architecture](architecture.md)**— how CI, the sandbox, and telemetry fit together
- :material-source-branch: **[CI Versions](ci-versions.md)**— GitLab CI vs GitHub Actions
- :material-list-checks: **[Step-by-step guide](getting-started.md)**— fresh clone → CI run
- :material-console: **[Tooling & Commands](tooling.md)**— Podman, tests, and lint commands

## Documentation workflow

These docs are built with [Zensical](https://zensical.org). Use `uv` for all
Python tooling:

```bash
uv run zensical serve    # live preview at http://localhost:8000
uv run zensical build    # generate the static site into site/
```
