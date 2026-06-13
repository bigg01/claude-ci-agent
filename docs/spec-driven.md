---
icon: lucide/scroll-text
---

# Spec-driven development in CI

The agent is at its best when a **written specification**— not a vague comment—
is the source of truth. You describe *what* to build and *how it will be judged*;
the agent implements against that spec, and a second, independent agent reviews the
result against the same spec. The spec is the contract both sides are held to.

```mermaid
flowchart LR
  S["spec/&lt;feature&gt;.md<br/>(the contract)"]
  A["Agent — read-write<br/>implements the spec"]
  R["Advisor — read-only<br/>reviews against the spec"]
  M["New PR / MR branch"]
  S --> A --> M --> R
  S --> R
  R -->|"gaps found"| A
  R -->|"meets spec"| H["Human merges"]
```

## Why a spec

- **Reviewable intent.** A spec is diffable and versioned— changes to *what we
  want* show up in history next to changes to *what we built*.
- **An objective bar.** The Advisor reviews against acceptance criteria you wrote,
  not against its own taste— so "looks fine to me" becomes "meets / misses spec
  item 3".
- **Separation of duties.** The Agent that writes the code never decides whether it
  passes— a different run (ideally a [different model or vendor](llm-gateway.md#different-models-or-vendors-for-creation-vs-review))
  judges it.

## 1. Write the spec

Keep specs in the repo so they are versioned, reviewed, and reachable by the agent.
A simple convention is one file per feature under `spec/`. The spec can be authored
by hand— or generated from a **Jira issue's** acceptance criteria when Jira is your
tracker (see [Triggering from Jira](#triggering-from-jira-with-gitlab) below):

```markdown
# spec/export-csv.md

## Goal
Let a user export their dashboard data as CSV from the report page.

## Acceptance criteria
- [ ] A "Download CSV" button appears on `/reports`.
- [ ] The CSV includes a header row and one row per record, UTF-8 encoded.
- [ ] Empty result sets produce a header-only file, not an error.
- [ ] A unit test covers the empty and non-empty cases.

## Out of scope
- Excel/XLSX export, scheduled exports.

## Constraints
- Follow CLAUDE.MD coding standards. No new third-party dependencies.
```

!!! tip "Acceptance criteria are the review rubric"

    Write them as checkboxes the Advisor can tick off one by one. Vague goals give
    vague reviews; testable criteria give a pass/fail verdict.

## 2. Implement from the spec (Agent personality)

Trigger the **read-write** [Agent](ci-versions.md#personalities-triggers) and point
its task at the spec file rather than describing the work inline. With the GitLab
component:

```yaml
include:
  - component: $CI_SERVER_FQDN/<group>/claude-ci-agent/claude-agent@v1
    inputs:
      prompt: >-
        Implement the specification in spec/export-csv.md exactly. Satisfy every
        acceptance criterion, add the tests it requires, and follow CLAUDE.MD.
        Do not implement anything listed under "Out of scope".
```

…or with the GitHub Action:

```yaml
- uses: bigg01/claude-ci-agent@v1
  with:
    prompt: >-
      Implement the specification in spec/export-csv.md exactly. Satisfy every
      acceptance criterion, add the tests it requires, and follow CLAUDE.MD.
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

The Agent works in the sandbox, makes atomic commits, and opens a **new branch /
PR**— it never pushes to the default branch (see
[Personalities & triggers](ci-versions.md#personalities-triggers)).

## 3. Review against the spec (Advisor personality)

When the PR/MR opens, the **read-only** Advisor runs automatically. Give it a prompt
that grades against the spec rather than reviewing in the abstract:

```text
You are the ADVISOR (read-only). Review this change against spec/export-csv.md.
For EACH acceptance criterion, state PASS or FAIL with the file:line evidence.
Run the tests and linters. List any criterion not met, any out-of-scope work that
slipped in, and any CLAUDE.MD violations. Write the verdict to review.md. Do not
modify files.
```

Because the Advisor holds **no write token**, it cannot "fix and approve" its own
finding— it can only report. The verdict is posted as a PR/MR comment, and the per-
run cost lands in [telemetry](observability.md#per-run-cost).

!!! tip "Independent reviewer"

    Run the Advisor on a *different* model or vendor than the Agent so the reviewer
    doesn't share the implementer's blind spots. See
    [Different models for creation vs review](llm-gateway.md#different-models-or-vendors-for-creation-vs-review).

## 4. Close the loop

The review feeds back into the same spec-driven cycle:

1. **Advisor reports FAIL on a criterion** → comment `@claude address review.md
   findings for spec/export-csv.md` to re-trigger the Agent on the existing branch.
2. **Spec was wrong, not the code** → edit `spec/export-csv.md`, and both the next
   implementation and the next review track the change automatically.
3. **All criteria PASS** → a human merges. The agent never self-approves a merge.

```mermaid
flowchart LR
  W["Write / refine spec"] --> I["Agent implements"]
  I --> V["Advisor grades vs spec"]
  V -->|FAIL| I
  V -->|"spec wrong"| W
  V -->|PASS| H["Human merges"]
```

## Triggering from Jira (with GitLab)

When GitLab is your SCM and **Jira** is your tracker, the **Jira issue is the
spec**— its description and acceptance criteria are the contract— and the issue's
**status drives the loop**. Moving a ticket to an "AI-Ready" state kicks off the
Agent; the Advisor's verdict flows back onto the ticket. Nothing new is needed in
the agent itself— only a trigger and two small API calls.

```mermaid
sequenceDiagram
  participant J as Jira issue (PROJ-123)
  participant GL as GitLab pipeline
  participant AG as Agent (read-write)
  participant AD as Advisor (read-only)
  participant H as Human
  J->>GL: status → "AI-Ready"<br/>Automation: web request → pipeline trigger
  GL->>AG: run with JIRA_ISSUE_KEY=PROJ-123
  AG->>J: fetch summary + acceptance criteria (REST)
  AG->>GL: implement → branch claude/PROJ-123 → open MR
  GL->>AD: MR opened → review vs the issue's criteria
  AD->>J: comment verdict (PASS/FAIL per criterion)
  AD->>J: transition (e.g. "In Review" / "Changes Requested")
  H->>J: merge MR → Smart Commit closes the issue
```

### 1. Jira side— fire on a status change

Add a **Jira Automation** rule: *When* issue transitions to `AI-Ready` (or gets a
`claude` label), *Then* **Send web request** to GitLab's
[pipeline-trigger API](https://docs.gitlab.com/ee/ci/triggers/), passing the issue
key as a variable:

```text
POST https://gitlab.example.com/api/v4/projects/<PROJECT_ID>/trigger/pipeline
form-encoded:
  token = {{ GitLab trigger token }}          # store in Jira's secret, not inline
  ref   = main
  variables[JIRA_ISSUE_KEY] = {{ issue.key }}
  variables[CLAUDE_TASK]    = Implement {{ issue.key }} from its acceptance criteria
```

`CLAUDE_TASK` makes the existing [Agent job](ci-versions.md#personalities-triggers)
rule (`if: $CLAUDE_TASK`) match— no pipeline change required to start.

### 2. GitLab side— materialize the spec and link back

In the Agent job, turn the Jira issue into the in-repo spec the loop already
expects, then name the branch with the issue key so GitLab's
[Jira integration](https://docs.gitlab.com/ee/integration/jira/) auto-links the MR
to the ticket:

```yaml
script:
  # Pull the issue → spec/<KEY>.md (JIRA_URL/JIRA_TOKEN from CI vars or OpenBao).
  # Jira Cloud returns the description as ADF (JSON); flatten its text nodes.
  - |
    curl -sS -H "Authorization: Bearer $JIRA_TOKEN" \
      "$JIRA_URL/rest/api/3/issue/$JIRA_ISSUE_KEY?fields=summary,description" \
      | python3 -c '
    import sys, json
    d = json.load(sys.stdin)["fields"]
    def text(node):
        if isinstance(node, dict):
            return node.get("text", "") + "".join(text(c) for c in node.get("content", []))
        return "".join(text(c) for c in node) if isinstance(node, list) else ""
    print("# %s\n\n%s" % (d["summary"], text(d.get("description") or {})))
    ' > "spec/$JIRA_ISSUE_KEY.md"
  - |
    claude -p "Implement spec/$JIRA_ISSUE_KEY.md exactly. Satisfy every acceptance \
    criterion, add the tests it requires, follow CLAUDE.MD." \
      --model "$CLAUDE_MODEL" --permission-mode bypassPermissions \
      --dangerously-skip-permissions
  # Branch + MR carry the issue key so Jira and GitLab cross-link automatically.
  - |
    git push "https://oauth2:${GIT_PUSH_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git" \
      "HEAD:claude/${JIRA_ISSUE_KEY}" \
      -o merge_request.create \
      -o merge_request.title="${JIRA_ISSUE_KEY} implement from spec"
```

### 3. Report the verdict back onto the ticket

When the Advisor finishes its review (MR-open trigger), post the verdict to the
issue and move it— so the loop is visible to non-engineers in Jira, not just in
GitLab:

```yaml
# In the Advisor job, after review.md is written:
- |
  jq -Rs '{body: {type:"doc", version:1, content:[{type:"paragraph",
    content:[{type:"text", text: .}]}]}}' review.md \
    | curl -sS -X POST -H "Authorization: Bearer $JIRA_TOKEN" \
        -H "Content-Type: application/json" \
        "$JIRA_URL/rest/api/3/issue/$JIRA_ISSUE_KEY/comment" -d @-
# …and transition, e.g. PASS → "In Review", FAIL → "Changes Requested":
- |
  curl -sS -X POST -H "Authorization: Bearer $JIRA_TOKEN" \
    -H "Content-Type: application/json" \
    "$JIRA_URL/rest/api/3/issue/$JIRA_ISSUE_KEY/transitions" \
    -d "{\"transition\":{\"id\":\"$JIRA_TRANSITION_ID\"}}"
```

### How the loop closes through Jira

- **FAIL** → the Advisor's comment lands on `PROJ-123`; a reviewer (or a follow-up
  `@claude` comment) re-triggers the Agent on the same branch. The ticket sits in
  "Changes Requested" until the next review passes.
- **Spec wrong, not the code** → edit the issue's acceptance criteria and move it
  back to `AI-Ready`; the regenerated `spec/PROJ-123.md` tracks the change.
- **PASS** → a human merges the MR. A [Smart Commit](https://support.atlassian.com/jira-software-cloud/docs/process-issues-with-smart-commits/)
  (`PROJ-123 #close`) in the merge transitions the issue to Done— the agent never
  self-merges or self-closes.

!!! note "Credentials stay zero-trust"

    The GitLab **trigger token** is scoped to one project; the **Jira API token**
    and `GIT_PUSH_TOKEN` come from CI variables or, better, the
    [OpenBao addon](secrets-openbao.md) at run time— nothing long-lived is baked
    into Jira or the pipeline. The read-only Advisor gets the Jira token to comment
    but **no** `GIT_PUSH_TOKEN`, so it still cannot change code.

## Guardrails that make this safe

- **The spec is in the repo**, so every run sees the same contract and its history.
- **Separation of duties**— writer and reviewer are different runs with different
  tokens; only the writer can change code, only humans can merge.
- **Everything is audited.** Each implement/review run streams secret-scrubbed
  OTLP events— and its [Anthropic cost](observability.md#per-run-cost)— to Elastic,
  so spec-driven work is fully attributable per feature, branch, and personality.
- **Bypass-permissions stays safe** because the agent runs
  [fully contained](yolo-mode.md)— the spec loop never lowers the sandbox boundary.
