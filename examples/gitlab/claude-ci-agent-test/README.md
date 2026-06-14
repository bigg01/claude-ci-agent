# Example: spec-driven loop on GitLab

A minimal **consuming project** that wires up the entire [Claude CI
agent](https://github.com/bigg01/claude-ci-agent) spec-driven loop with a single
`include:`. Copy this layout into any GitLab project to try it.

```
.
├── .gitlab-ci.yml      # one include → both personalities
└── spec/
    └── feature01.md    # the contract the agent implements and the advisor grades
```

## How it works

[`.gitlab-ci.yml`](.gitlab-ci.yml) includes the `claude-agent` component, which
ships **both personalities** — so you don't hand-write any agent/advisor jobs:

| Job | Runs when | Does |
| --- | --- | --- |
| `claude-agent` (read-write) | you click it (gated to `manual` here) | Implements [`spec/feature01.md`](spec/feature01.md) on a new branch, commits, and opens a merge request |
| `claude-advisor` (read-only) | a merge request opens / updates | Grades the diff against the spec and posts the verdict as an MR note |

The advisor is pinned to a cheaper, faster model (`claude-haiku-4-5`) than the
agent (`claude-sonnet-4-6`) so the reviewer doesn't share the implementer's blind
spots.

## Run it

1. **Set the required CI/CD variables** (Settings → CI/CD → Variables; mask + protect):
   - `ANTHROPIC_API_KEY` — your Anthropic API key.
   - `GITLAB_TOKEN` — a token with `api` scope (the agent pushes the branch and
     opens the MR; the advisor posts the review note). `CI_JOB_TOKEN` is **not**
     sufficient.
   - *(optional)* `ELASTIC_OTLP_ENDPOINT` / `ELASTIC_OTLP_AUTHORIZATION` to stream
     the secret-scrubbed audit trail and per-run cost to Elastic.
2. **Pin the component version.** This example uses `@v0.1.0-alpha.8`; bump it to
   the latest [release](https://github.com/bigg01/claude-ci-agent/releases) and
   update the matching image tag the component pins.
3. **Click `claude-agent`** in the pipeline. It implements the spec and opens an
   MR — and the advisor auto-runs on that MR to grade it.

## Learn more

- [Spec-driven development in CI](https://bigg01.containerize.ch/claude-ci-agent/spec-driven/)
- [CI versions & the GitLab component](https://bigg01.containerize.ch/claude-ci-agent/ci-versions/)
