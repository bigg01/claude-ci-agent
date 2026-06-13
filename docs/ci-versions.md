---
icon: lucide/git-branch
---

# CI Versions

This project runs in two CI flavors. Detect which one you are in via environment
variables (`$GITLAB_CI` vs `$GITHUB_ACTIONS`) and behave accordingly.

!!! note "This repo: GitHub source, GitLab mirror"

    The repository is **developed on GitHub** — its own CI (tests, image build,
    advisor/agent) runs in [`.github/workflows/`](https://github.com/bigg01/claude-ci-agent/tree/main/.github/workflows).
    It is **mirrored read-only to GitLab**, whose only pipeline is a tagged
    release that publishes the `claude-agent` component to the CI/CD Catalog. So
    on GitLab you *consume* the component — you don't run this project's pipeline.
    The table below describes how the agent behaves in each CI once you wire it
    into **your** project.

=== "GitLab CI"

    | Aspect | Value |
    | --- | --- |
    | **Runner** | Rootless, unprivileged Podman on an OpenShift GitLab Runner |
    | **Pipeline config** | `include:` the `claude-agent` [component](https://github.com/bigg01/claude-ci-agent/blob/main/templates/claude-agent.yml) in your `.gitlab-ci.yml` |
    | **Detection** | `$GITLAB_CI == "true"` |
    | **Telemetry** | OTel Collector sidecar at `http://localhost:4318` (mandatory) |
    | **Builds** | Podman (`podman build -t app-test .`)— never Docker |
    | **Credentials** | Zero-credential; no global Git/SSH keys or Elastic token |

=== "GitHub Actions"

    | Aspect | Value |
    | --- | --- |
    | **Runner** | GitHub-hosted or self-hosted runner |
    | **Pipeline config** | `.github/workflows/*.yml` |
    | **Detection** | `$GITHUB_ACTIONS == "true"` |
    | **Telemetry** | OTel Collector via workflow service/sidecar at `http://localhost:4318` when configured |
    | **Builds** | Prefer Podman to mirror GitLab; fall back to Docker only if the workflow provisions it |
    | **Credentials** | Workflow-scoped `GITHUB_TOKEN`/secrets— do not read host OS env vars |

## Zero-credential environment

The sandbox image ships with **no ambient credentials**— no global Git config,
no SSH keys, no cloud profiles, and no long-lived tokens baked in. The agent is
also instructed never to read host OS environment variables (see
[`CLAUDE.MD`](https://github.com/bigg01/claude-ci-agent/blob/main/CLAUDE.MD)). Every
secret it needs is injected **per run**, scoped to that run by the CI platform's
secret store, and gone when the job ends. The mechanism differs by platform:

=== "GitLab CI"

    - **Source— masked, protected CI/CD variables.** The team's
      `ANTHROPIC_API_KEY` and the write-scoped `GIT_PUSH_TOKEN` are provided as
      CI/CD variables at the project or **group** level (one key shared across a
      team). _Masked_ redacts them from job logs; _protected_ restricts them to
      protected branches and tags.
    - **Fail-fast, not silent.** Both personalities guard on the key in
      `before_script` and exit with instructions if it is missing— the team is
      explicitly asked to set it rather than hitting a cryptic mid-run error.
    - **No host credentials.** The job runs as an arbitrary non-root UID in a
      rootless OpenShift runner pod; the only platform credentials present are
      the ones GitLab grants the job (e.g. `$CI_REGISTRY_*` for image push).
    - **Boundary by absence.** The read-only Advisor is issued **no**
      `GIT_PUSH_TOKEN` at all, so mutation is impossible even if attempted.
    - **Optional— no stored secret at all.** With the
      [OpenBao addon](secrets-openbao.md), the job mints a short-lived OIDC JWT
      (`id_tokens:` → `BAO_JWT`) and exchanges it for a lease-bound secret at
      runtime— nothing long-lived is stored in GitLab.

=== "GitHub Actions"

    - **Source— the `secrets` context.** `${{ secrets.ANTHROPIC_API_KEY }}` is
      injected as an env var only into the steps that reference it and is
      auto-masked in logs.
    - **Repo token is ephemeral.** Writes use the per-job `GITHUB_TOKEN`, freshly
      minted each run and expired when the job ends— never a personal token.
    - **Least privilege per personality.** The job's `permissions:` block sets
      scope: the Advisor declares `contents: read` (it literally cannot push),
      the Agent declares `contents: write` and only ever opens a new branch.
    - **Optional— no stored secret at all.** With `permissions: id-token: write`,
      the [OpenBao addon](secrets-openbao.md) uses GitHub OIDC to mint a JWT
      exchanged for a vault secret at runtime— the same model as GitLab.

!!! info "Same guarantee, two stores"

    On both platforms the secret is short-lived, scoped to the run, masked in
    logs, and never written to the image. Because the agent cannot reach the host
    OS environment, an escaped or hallucinated credential lookup finds nothing—
    and every action it does take is OTel-audited. This is what makes
    [bypass-permissions ("YOLO") mode](yolo-mode.md) safe here.

!!! tip "Prefer short-lived Anthropic keys"

    Give CI a **short-lived, rotated** Anthropic API key rather than a permanent
    one— scope it to a dedicated **workspace** with a **spend limit**, rotate it
    on a schedule, and revoke it the moment a run leaks it. Better still, store no
    static key at all: have the [OpenBao addon](secrets-openbao.md) mint one with
    a short lease, or federate via OIDC so each run receives an ephemeral
    credential that expires on its own.

    **Why it matters —** the API key is the one credential a leak actually
    monetizes: unlike the repo token (scoped, ephemeral, useless off this repo) it
    bills straight to your Anthropic account. A CI variable is exposed to every
    job, every log line, the build cache, and— on fork merge requests— to code
    you did not write; masking reduces but never eliminates that exposure. A key
    that is short-lived, workspace-scoped, and spend-capped shrinks both the
    **window** an exfiltrated key stays valid and the **blast radius** of spend if
    it is used before you notice.

## Detecting the environment

```bash
if [ "$GITLAB_CI" = "true" ]; then
  echo "Running under GitLab CI"
elif [ "$GITHUB_ACTIONS" = "true" ]; then
  echo "Running under GitHub Actions"
fi
```

## Personalities & triggers

The same image runs as one of two personalities, selected by the CI trigger:

=== "Agent— read-write"

    | Aspect | Value |
    | --- | --- |
    | **Trigger** | A `@claude …` comment on a PR/issue (GitHub `issue_comment`; GitLab via a comment-driven pipeline passing `$CLAUDE_TASK`) |
    | **Does** | Applies a fix, commits, opens a **new** PR/MR branch |
    | **Token** | Repository **write**— confined to new branches, never the default branch |

=== "Advisor— read-only"

    | Aspect | Value |
    | --- | --- |
    | **Trigger** | A PR/MR **open** or **synchronize** event (GitHub `pull_request`; GitLab `merge_request_event`) |
    | **Does** | Lints, tests, flags bugs, posts a review comment— never mutates |
    | **Token** | Repository **read** + permission to post review comments |

!!! tip "Run creation and review on different models or vendors"

    Because the two personalities do opposite jobs against a shared written spec,
    it makes sense to give them **different models— or different vendors**: the
    Agent creates on the strongest coding model, while the Advisor reviews with an
    *independent* one that doesn't share the creator's blind spots. See
    [Different models for creation vs review](llm-gateway.md#different-models-or-vendors-for-creation-vs-review).

## Identity & attribution— who did what

Give every agent its **own GitLab identity**— a dedicated **service account
(bot user)** whose access token it authenticates with. Never reuse a human's
Personal Access Token, and never share one token across personalities or teams:
if two agents push with the same credential, the audit log cannot tell them
apart. The read-write Agent gets a write-scoped token; the read-only Advisor gets
no push token at all (but still its own bot, so the review comments it posts are
attributable).

Attribution then lands in **three independent places that should always agree**—
if one disagrees, you have a misconfiguration:

1. **GitLab audit log + MR author** → the **bot user** the access token belongs to.
2. **`git log` author/committer** → the **git identity** (set it to match the bot).
3. **Commit trailers + OTel attributes** (`claude.personality`, `ci.pipeline.id`) → the **specific run**.

### Naming example

One identity per *(personality × team)*. For a read-write Agent on a `payments`
team:

| Thing | Convention | Example |
| --- | --- | --- |
| GitLab service account (bot user) | `claude-<personality>[-<team>]` | `claude-agent-payments` |
| Access token name (so you revoke the right one) | `<bot>-<scope>-<created>` | `claude-agent-payments-write-2026-06` |
| Git author name | `Claude <Personality> · <team>` | `Claude Agent · payments` |
| Git author email (plus-addressed: unique yet routable) | `claude-<personality>+<team>@<org>` | `claude-agent+payments@acme.dev` |
| Branch / MR | `claude/<personality>/<pipeline-id>-<short-sha>` | `claude/agent/84213-1a2b3c4` |
| Commit trailers (pin a change to one run) | `Claude-Run`, `Claude-Model`, `Claude-Bot` | `Claude-Run: gitlab/pipeline/84213/job/99001` |

So a commit the agent makes carries, for example:

```text
feat: handle null customer in checkout

Claude-Personality: agent
Claude-Bot: claude-agent-payments
Claude-Run: gitlab/pipeline/84213/job/99001
Claude-Model: claude-sonnet-4-6
```

!!! tip "Map the git email to the bot"

    In GitLab, add the git author email as a (verified or `noreply`) email on the
    bot user, so `git log` entries link back to the same account the audit log and
    MR list show. Otherwise commits render as an *unattributed* author even though
    the push itself was the bot— and your three sources no longer agree.

!!! note "GitHub equivalent"

    The per-job `GITHUB_TOKEN` always authors as `github-actions[bot]`— shared
    across every workflow, so it can't distinguish agents. For unique identities,
    install a **GitHub App per agent** (app slug e.g. `claude-agent[bot]`) or issue
    distinct fine-grained PATs, and set the same `user.name` / `user.email` and
    commit-trailer convention. Attribution then comes from the App identity (audit
    log + PR author) plus the trailers.

## Example pipelines

### GitLab CI— using the `claude-agent` component

A reusable [GitLab CI/CD component](https://docs.gitlab.com/ee/ci/components/)
ships with this project at
[`templates/claude-agent.yml`](https://github.com/bigg01/claude-ci-agent/blob/main/templates/claude-agent.yml).
It runs the agent inside the sandbox image with OTel telemetry enabled and
defaults to bypass-permissions ("YOLO") mode— safe here because the agent is
[fully contained](yolo-mode.md).

Reference it from your `.gitlab-ci.yml`:

```yaml
stages:
  - test

include:
  - component: $CI_SERVER_FQDN/<group>/claude-ci-agent/claude-agent@main
    inputs:
      prompt: "Fix the failing unit tests and commit the change."
```

!!! note "Replace the component path"

    `<group>` must point at the GitLab project that hosts this component. Pin
    `@main` to a tag or commit SHA for reproducible pipelines.

#### Inputs

| Input | Default | Description |
| --- | --- | --- |
| `stage` | `test` | Pipeline stage the job runs in. |
| `image` | `app-test` | Container image providing the Claude Code CLI. |
| `prompt` | _(required)_ | The task prompt handed to the agent. |
| `api_key_variable` | `ANTHROPIC_API_KEY` | **Name** of the masked, protected CI/CD variable holding your team's Anthropic key— never the key itself. The job fails fast if it is unset. |
| `claude_args` | `--dangerously-skip-permissions` | Extra flags for the `claude` CLI; set empty to require approvals. |
| `otel_endpoint` | `http://localhost:4318` | OTLP endpoint of the OTel Collector sidecar. |

!!! warning "Provide the key as a variable, not an input"

    Pass the variable **name** via `api_key_variable`, then create that masked,
    protected CI/CD variable with your team's key. Component inputs are
    interpolated as plaintext into the compiled pipeline, so passing the key
    directly would leak it.

### GitHub Actions— using the `claude-ci-agent` action

The GitHub analog of the GitLab component is a reusable **Docker container action**
at [`action.yml`](https://github.com/bigg01/claude-ci-agent/blob/main/action.yml).
It runs the agent inside the same sandbox image and takes the same kind of inputs.
Reference it from any workflow with `uses:`:

```yaml
name: Claude Agent
on: [workflow_dispatch]
jobs:
  agent:
    runs-on: ubuntu-latest
    steps:
      - uses: bigg01/claude-ci-agent@v1
        with:
          prompt: "Fix the failing unit tests and commit the change."
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

#### Inputs

| Input | Default | Description |
| --- | --- | --- |
| `prompt` | _(required)_ | The task prompt handed to the agent. |
| `anthropic_api_key` | _(required)_ | Anthropic API key— pass from `${{ secrets.* }}`, never inline. The action fails fast if empty. |
| `claude_args` | `--dangerously-skip-permissions` | Extra flags for the `claude` CLI; set empty to require approvals. |
| `model` | `claude-sonnet-4-6` | Claude model id. |
| `otel_endpoint` | `http://localhost:4318` | OTLP endpoint of the OTel Collector sidecar. |

!!! note "Two GitHub surfaces"

    - [`action.yml`](https://github.com/bigg01/claude-ci-agent/blob/main/action.yml)—
      the reusable component above, for *other* repos.
    - [`.github/workflows/claude-agent.yml`](https://github.com/bigg01/claude-ci-agent/blob/main/.github/workflows/claude-agent.yml)—
      this repo's event-driven workflow (build image → advisor on PRs → agent on
      `@claude` comments), the analog of the GitLab *pipeline*.

For the reusable action, the secret is passed via the `secrets` context (auto-masked
in logs); the action itself never sees it as a plaintext input.
