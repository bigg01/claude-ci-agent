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

## Setting the Anthropic API key

The agent needs an `ANTHROPIC_API_KEY`. Store it in the platform's secret store—
**never** in the repo, the pipeline YAML, or a component/action input.

=== "GitHub Actions"

    **UI** — repo **Settings → Secrets and variables → Actions → New repository
    secret** (or an **organization** secret to share across repos):

    | Field | Value |
    | --- | --- |
    | Name | `ANTHROPIC_API_KEY` |
    | Secret | your `sk-ant-…` key |

    **CLI:**

    ```sh
    gh secret set ANTHROPIC_API_KEY            # prompts for the value
    # or: gh secret set ANTHROPIC_API_KEY --body "sk-ant-..." --repo bigg01/your-repo
    ```

    **Use it** — pass it into the action via the `secrets` context (it's masked in
    logs and only exposed to steps that reference it):

    ```yaml
    - uses: bigg01/claude-ci-agent@v0.1.0-alpha.4
      with:
        prompt: "Fix the failing tests."
        anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    ```

=== "GitLab CI"

    **UI** — project (or **group**, to share across a team) **Settings → CI/CD →
    Variables → Add variable**:

    | Field | Value |
    | --- | --- |
    | Key | `ANTHROPIC_API_KEY` |
    | Value | your `sk-ant-…` key |
    | Flags | ✔ **Masked**, ✔ **Protected**, **Expand variable reference** off |

    **CLI** ([`glab`](https://gitlab.com/gitlab-org/cli)):

    ```sh
    glab variable set ANTHROPIC_API_KEY "sk-ant-..." --masked --protected
    ```

    **Use it** — the [component](#gitlab-ci-using-the-claude-agent-component) reads
    the variable **by name** (don't pass the key as an input); just include it:

    ```yaml
    include:
      - component: $CI_SERVER_FQDN/<group>/claude-ci-agent/claude-agent@v0.1.0-alpha.4
        inputs:
          prompt: "Fix the failing tests."
    ```

!!! warning "Protected variable ⇒ protected ref"

    A GitLab **Protected** variable is only injected on **protected** branches/tags.
    If a pipeline runs on an unprotected branch, `ANTHROPIC_API_KEY` is empty and the
    job fails fast. Protect the branch, or drop the Protected flag for testing.

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

The same image runs as one of two personalities, selected by the CI trigger. On
GitLab both are shipped **by the component** as two jobs — `claude-advisor`
(gated on `merge_request_event`) and `claude-agent` (gated on a non-empty
`$CLAUDE_TASK`) — so a single `include:` wires up the full flow; you don't
hand-write them (see [Example pipelines](#gitlab-ci-using-the-claude-agent-component)).
On GitHub the analog is the event-driven [workflow](https://github.com/bigg01/claude-ci-agent/blob/main/.github/workflows/claude-agent.yml).

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
A single `include:` adds **both personalities** as jobs — at parity with the
GitHub workflow:

- **`claude-advisor`** (read-only) runs automatically on every
  `merge_request_event`: it reviews the diff and posts the verdict as an MR note.
- **`claude-agent`** (read-write) runs when `$CLAUDE_TASK` is non-empty (from the
  `prompt` input, or a pipeline variable supplied by a manual run / trigger token
  / webhook — GitLab has no native "MR comment" trigger): it applies the change
  on a new branch and opens a **new MR**, never the default branch.

Both jobs start an **OTel Collector sidecar** (nested Podman) when
`ELASTIC_OTLP_ENDPOINT` is set, emit per-run cost, optionally fetch secrets via
the [OpenBao addon](secrets-openbao.md), and default to bypass-permissions
("YOLO") mode — safe here because the agent is [fully contained](yolo-mode.md).

!!! note "Runner must allow nested Podman"

    The OTel sidecar runs as nested rootless Podman inside the sandbox image
    (the choice that mirrors the GitHub container job). Use a privileged or
    rootless-Podman-capable runner. If yours can't, leave `ELASTIC_OTLP_ENDPOINT`
    unset to skip the sidecar — the agent still runs; only the exported audit
    trail is lost.

**Step 1 — set the Anthropic key as a CI/CD variable** (this is how the key is
provided; it is **never** a component input). In the consuming project (or group):
**Settings → CI/CD → Variables → Add variable**:

| Field | Value |
| --- | --- |
| Key | `ANTHROPIC_API_KEY` |
| Value | your `sk-ant-…` key |
| Flags | ✔ **Masked**, ✔ **Protected**, **Expand variable reference** off |

**Step 2 — include the component** in your `.gitlab-ci.yml`:

```yaml
stages:
  - test

include:
  - component: $CI_SERVER_FQDN/<group>/claude-ci-agent/claude-agent@v0.1.0-alpha.4
    inputs:
      prompt: "Fix the failing unit tests and commit the change."
      # api_key_variable: MY_KEY_NAME   # only if your variable isn't ANTHROPIC_API_KEY
```

The component reads the variable **by name** at runtime and exports it for the
`claude` CLI — fail-fast if it's unset.

!!! note "Replace the component path and pin a version"

    `<group>` must point at the GitLab project that hosts this component. Pin
    `@v0.1.0-alpha.4` to a released tag (or a commit SHA) for reproducible pipelines.

!!! warning "Protected variable ⇒ protected ref"

    A **Protected** variable is only injected on **protected** branches/tags. If the
    pipeline runs on an unprotected branch, `ANTHROPIC_API_KEY` is empty and the job
    fails fast — either protect the branch or drop the Protected flag.

#### Inputs

| Input | Default | Description |
| --- | --- | --- |
| `stage` | `test` | Pipeline stage both jobs run in. |
| `image` | `ghcr.io/bigg01/claude-ci-agent/claude-agent:0.1.0-alpha.4` | Published sandbox image providing the Claude Code CLI + baked CI helpers. |
| `prompt` | `""` | Task handed to the **agent** personality. Leave empty for advisor-only use; a `CLAUDE_TASK` pipeline variable overrides it for ad-hoc agent runs. |
| `model` | `claude-sonnet-4-6` | Claude model id passed to `claude --model`. |
| `api_key_variable` | `ANTHROPIC_API_KEY` | **Name** of the masked, protected CI/CD variable holding your team's Anthropic key— never the key itself. The job fails fast if it is unset. |
| `token_variable` | `GITLAB_TOKEN` | **Name** of the variable holding a GitLab token (`api` scope) used to post MR notes (advisor) and open MRs (agent). `CI_JOB_TOKEN` is not sufficient. |
| `claude_args` | `--dangerously-skip-permissions` | Extra flags for the `claude` CLI; set empty to require approvals. |
| `otel_endpoint` | `http://localhost:4318` | OTLP endpoint the agent exports to (the sidecar listens here). |
| `team` | `default` | `team.name` resource attribute, for per-team cost attribution. |
| `bao_audience` | `$CI_SERVER_URL` | Audience (`aud`) of the OIDC JWT minted for the optional [OpenBao addon](secrets-openbao.md). |

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
| `prompt` | *(required)* | The task prompt handed to the agent. |
| `anthropic_api_key` | *(required)* | Anthropic API key— pass from `${{ secrets.* }}`, never inline. The action fails fast if empty. |
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

## Complete scenario— GitLab + Jira, spec-driven

This ties the pieces together: a **Jira issue is the spec**, a status change kicks
off GitLab, the read-write **Agent** implements it, the read-only **Advisor** grades
the MR against that same spec, and the verdict flows back onto the ticket. The
deeper rationale lives in [Spec-driven development](spec-driven.md#triggering-from-jira-with-gitlab);
this is the concrete GitLab wiring.

### Timeline

1. A PO writes acceptance criteria on **`PROJ-142`** and moves it to **AI-Ready**.
2. A **Jira Automation** rule fires a web request to GitLab's pipeline-trigger API,
   passing `JIRA_ISSUE_KEY=PROJ-142`.
3. The **`implement`** job pulls the issue → `spec/PROJ-142.md`, the Agent implements
   to spec, opens MR **`claude/PROJ-142`**, comments on Jira, and moves it to **In Review**.
4. The MR-open event runs the **`advisor`** job: it grades each criterion against the
   spec, posts **PASS/FAIL** on the MR *and* on Jira, and transitions the issue.
5. **PASS** → a human merges; a [Smart Commit](https://support.atlassian.com/jira-software-cloud/docs/process-issues-with-smart-commits/)
   (`PROJ-142 #close`) closes the ticket. **FAIL** → a reviewer re-triggers the Agent
   on the same branch. The agent never self-merges.

### Jira side— the trigger

A Jira Automation rule, *When* issue transitions to `AI-Ready`, *Then* **Send web
request** (store the GitLab trigger token in Jira's secret vault, not inline):

```text
POST https://gitlab.example.com/api/v4/projects/<PROJECT_ID>/trigger/pipeline
form-encoded:
  token = {{ GitLab trigger token }}
  ref   = main
  variables[JIRA_ISSUE_KEY] = {{ issue.key }}
```

### GitLab side— the complete `.gitlab-ci.yml`

Set as CI/CD variables (masked/protected, or minted at runtime by the
[OpenBao addon](secrets-openbao.md)): `ANTHROPIC_API_KEY`, `JIRA_URL`, `JIRA_TOKEN`,
`GIT_PUSH_TOKEN` (the Agent bot's write token), and the Jira transition IDs.

```yaml
stages: [implement, review]

variables:
  AGENT_IMAGE: ghcr.io/bigg01/claude-ci-agent/claude-agent:0.1.0-alpha.4
  CLAUDE_MODEL: "claude-sonnet-4-6"
  CLAUDE_CODE_ENABLE_TELEMETRY: "1"
  OTEL_LOG_TOOL_CONTENT: "1"
  OTEL_EXPORTER_OTLP_ENDPOINT: http://localhost:4318

# Shared Jira helpers, injected into each job's before_script as shell functions.
.jira_fns: &jira_fns |
  jira_to_spec() {            # Jira issue → spec/<KEY>.md (Jira Cloud returns ADF JSON)
    mkdir -p spec
    curl -sS -H "Authorization: Bearer $JIRA_TOKEN" \
      "$JIRA_URL/rest/api/3/issue/$JIRA_ISSUE_KEY?fields=summary,description" \
    | python3 -c '
  import sys, json
  d = json.load(sys.stdin)["fields"]
  def t(n): return (n.get("text","")+"".join(t(c) for c in n.get("content",[]))) if isinstance(n,dict) else "".join(t(c) for c in n) if isinstance(n,list) else ""
  print("# %s\n\n%s" % (d["summary"], t(d.get("description") or {})))' > "spec/$JIRA_ISSUE_KEY.md"
  }
  jira_comment() {            # post the contents of $1 as a comment on the issue
    jq -Rs '{body:{type:"doc",version:1,content:[{type:"paragraph",content:[{type:"text",text:.}]}]}}' "$1" \
    | curl -sS -X POST -H "Authorization: Bearer $JIRA_TOKEN" -H "Content-Type: application/json" \
        "$JIRA_URL/rest/api/3/issue/$JIRA_ISSUE_KEY/comment" -d @-
  }
  jira_transition() {         # move the issue to transition id $1
    curl -sS -X POST -H "Authorization: Bearer $JIRA_TOKEN" -H "Content-Type: application/json" \
      "$JIRA_URL/rest/api/3/issue/$JIRA_ISSUE_KEY/transitions" -d "{\"transition\":{\"id\":\"$1\"}}"
  }

# ---- AGENT (read-write): Jira-triggered implementation -----------------------
implement:
  stage: implement
  image: $AGENT_IMAGE
  rules:
    - if: '$JIRA_ISSUE_KEY'            # only on the Jira-triggered pipeline
  before_script:
    - *jira_fns
    - git config user.name  "Claude Agent · payments"
    - git config user.email "claude-agent+payments@acme.dev"
  script:
    - jira_to_spec
    - |
      claude -p "Implement spec/$JIRA_ISSUE_KEY.md exactly. Satisfy every acceptance \
      criterion, add the tests it requires, follow CLAUDE.MD. Nothing out of scope." \
        --model "$CLAUDE_MODEL" --permission-mode bypassPermissions \
        --dangerously-skip-permissions
    # New branch named with the Jira key → GitLab/Jira auto-link the MR to the issue.
    - |
      git checkout -b "claude/$JIRA_ISSUE_KEY"
      git add -A
      git commit -m "feat($JIRA_ISSUE_KEY): implement from spec" \
        -m "Claude-Personality: agent" \
        -m "Claude-Run: gitlab/pipeline/$CI_PIPELINE_ID"
      git push "https://oauth2:${GIT_PUSH_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git" \
        "HEAD:claude/$JIRA_ISSUE_KEY" \
        -o merge_request.create \
        -o merge_request.title="$JIRA_ISSUE_KEY implement from spec"
    - echo "Claude opened an implementation MR for review." > _msg.txt && jira_comment _msg.txt
    - jira_transition "$JIRA_IN_REVIEW_ID"

# ---- ADVISOR (read-only): grade the MR against the spec ----------------------
advisor:
  stage: review
  image: $AGENT_IMAGE
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event" && $CI_MERGE_REQUEST_SOURCE_BRANCH_NAME =~ /^claude\//'
  variables:
    JIRA_ISSUE_KEY: "$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME"   # claude/PROJ-142 → stripped below
  before_script:
    - *jira_fns
    - 'export JIRA_ISSUE_KEY="${JIRA_ISSUE_KEY#claude/}"'
  script:
    - |
      claude -p "You are the ADVISOR (read-only). Review this MR against \
      spec/$JIRA_ISSUE_KEY.md. For EACH acceptance criterion, state PASS or FAIL with \
      file:line evidence. Run the tests and linters. Note any out-of-scope work or \
      CLAUDE.MD violations. Write the verdict to review.md. Do NOT modify files." \
        --model "$CLAUDE_MODEL" --permission-mode bypassPermissions \
        --dangerously-skip-permissions
    # Post the verdict to the MR (bot API token) and to Jira, then transition.
    - |
      jq -Rs '{body: .}' review.md | curl -sS -X POST \
        -H "PRIVATE-TOKEN: $GIT_PUSH_TOKEN" -H "Content-Type: application/json" \
        "$CI_API_V4_URL/projects/$CI_MERGE_REQUEST_PROJECT_ID/merge_requests/$CI_MERGE_REQUEST_IID/notes" -d @-
    - jira_comment review.md
    - |
      grep -q 'FAIL' review.md && jira_transition "$JIRA_CHANGES_REQUESTED_ID" \
                               || jira_transition "$JIRA_IN_REVIEW_ID"
  artifacts:
    paths: [review.md]
    expire_in: 1 week
```

!!! note "Why the Advisor stays safe here"

    The Advisor gets the **Jira token** (to comment + transition) and a token to post
    the MR note, but **no `GIT_PUSH_TOKEN` for code**— it cannot change the branch it
    is reviewing. Both jobs are
    [fully contained](yolo-mode.md), and every step streams secret-scrubbed OTLP to
    Elastic, tagged with `JIRA_ISSUE_KEY` so the whole feature is auditable end to end.
