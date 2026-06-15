# `claude-agent` — GitLab CI/CD component

Run [Claude Code](https://docs.claude.com/claude-code) in your GitLab pipeline as
two personalities, inside a rootless, OTel-instrumented sandbox image — at parity
with the [GitHub Action](../action.yml). One `include:` wires up both.

| Job | Personality | Triggers when | Does |
| --- | --- | --- | --- |
| `claude-advisor` | **read-only** | a `merge_request_event` | Reviews the diff, runs linters/tests, writes `review.md`, posts it as an **MR note**. Holds no write token — it cannot mutate. |
| `claude-agent` | **read-write** | `CLAUDE_TASK` is non-empty (the `prompt` input, or a `CLAUDE_TASK` pipeline variable from a manual run / trigger / webhook) | Implements the task on a **new** `claude/task-<pipeline_id>` branch and opens an MR — never pushes to the default branch. |

## Quick start

In the consuming project's `.gitlab-ci.yml`:

```yaml
stages:
  - test

include:
  - component: $CI_SERVER_FQDN/<group>/claude-ci-agent/claude-agent@v0.1.0-alpha.12
    inputs:
      # Advisor needs no prompt. The agent runs this (or a CLAUDE_TASK variable):
      prompt: "Fix the failing unit tests and commit the change."
```

Pin `@<version>` to a [released tag](https://github.com/bigg01/claude-ci-agent/releases)
(or a commit SHA) for reproducible pipelines.

## Required CI/CD variables

Set these under **Settings → CI/CD → Variables** (mask + protect secrets); a group
variable shares them across a team.

| Variable | Needed by | Notes |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | both | Your Anthropic key. Read **by name** (never passed as an input — inputs interpolate as plaintext). Name overridable via `api_key_variable`. |
| `GITLAB_TOKEN` | agent (push + MR), advisor (MR note) | Project/group access token with the **`write_repository`** *and* **`api`** scopes and at least the **Developer** role. A read-only token gets a `403 You are not allowed to push code` on `git push`. `CI_JOB_TOKEN` is **not** sufficient. Name overridable via `token_variable`. |

### Optional

| Variable(s) | Purpose |
| --- | --- |
| `ELASTIC_OTLP_ENDPOINT`, `ELASTIC_OTLP_AUTHORIZATION` | Stream the secret-scrubbed audit trail + per-run cost to Elastic. No OTel sidecar starts unless `ELASTIC_OTLP_ENDPOINT` is set. |
| `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` | Corporate proxy. Honored by `claude`, `git`, and `curl`, mirrored to upper/lower case, and forwarded into the OTel sidecar. `localhost`/`127.0.0.1` are auto-added to `NO_PROXY` so the OTLP export is never proxied — add your internal GitLab/Elastic hosts to `NO_PROXY` yourself. |
| `BAO_ADDR`, `BAO_ROLE`, `BAO_SECRET_PATH` | [OpenBao addon](../addons/openbao): the job mints a short-lived OIDC JWT and exchanges it for secrets at runtime — nothing long-lived is stored. |

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `stage` | `test` | Pipeline stage both jobs run in. |
| `image` | `ghcr.io/bigg01/claude-ci-agent/claude-agent:0.1.0-alpha.12` | The published sandbox image (Claude Code CLI + baked CI helpers). Pin to a released tag; override to a mirror. |
| `prompt` | `""` | Task for the **agent**. Leave empty for advisor-only use; a `CLAUDE_TASK` pipeline variable overrides it. |
| `branch_prefix` | `claude/task-` | Prefix for the agent's branch; the pipeline id is appended (e.g. `claude/task-1234`). Keep in sync with any advisor `rules:` that match on the branch name. |
| `model` | `claude-sonnet-4-6` | Claude model id passed to `claude --model`. Use a capable model for the **implementer** — a small model like `haiku` often stalls on autonomous multi-file work. |
| `api_key_variable` | `ANTHROPIC_API_KEY` | **Name** of the variable holding your Anthropic key. |
| `token_variable` | `GITLAB_TOKEN` | **Name** of the variable holding the GitLab token (see above). |
| `claude_args` | `--dangerously-skip-permissions` | Extra flags for `claude`. Bypass-permissions ("YOLO") is safe because the job is [fully contained](https://bigg01.containerize.ch/claude-ci-agent/yolo-mode/); set to `""` to require approvals. |
| `otel_endpoint` | `http://localhost:4318` | OTLP endpoint the agent exports to (the sidecar listens here). |
| `team` | `default` | `team.name` resource attribute, for per-team cost attribution. |
| `bao_audience` | `$CI_SERVER_URL` | Audience (`aud`) of the OIDC JWT minted for the OpenBao addon. |

> **Model precedence gotcha:** a project/group `CLAUDE_MODEL` CI/CD variable
> **overrides** the per-job model this component sets — so it can silently force the
> *agent* onto the advisor's cheaper model. Prefer the `model` input, and don't set
> a global `CLAUDE_MODEL` unless you mean it for every job.

## How it runs

`claude` runs **directly in the job's container**, which *is* the rootless sandbox
image (the runner starts the job in it via `image:`) — not in a nested `podman run`.
Nested Podman is used only for the OTel sidecar and for any app images the agent
itself builds. So a plain run needs no nested Podman; if your runner can't do
nested rootless Podman, leave `ELASTIC_OTLP_ENDPOINT` unset to skip the sidecar.

## Customizing

Because both jobs `extends: ".claude-base"` (the component's hidden base — secret
resolution, proxy normalization, OTel sidecar, teardown), you can override or add
jobs in your `.gitlab-ci.yml`. For example, gate the agent behind a manual click,
disable the built-in advisor, and add a spec-graded reviewer on a cheaper model —
see the runnable [`examples/gitlab/claude-ci-agent-test/`](../examples/gitlab/claude-ci-agent-test/).

## Docs

- [CI versions](https://bigg01.containerize.ch/claude-ci-agent/ci-versions/)
- [Spec-driven development](https://bigg01.containerize.ch/claude-ci-agent/spec-driven/)
- [Sandboxing & YOLO mode](https://bigg01.containerize.ch/claude-ci-agent/yolo-mode/)
- [Observability](https://bigg01.containerize.ch/claude-ci-agent/observability/)
