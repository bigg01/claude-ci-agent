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
A simple convention is one file per feature under `spec/`:

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

## Guardrails that make this safe

- **The spec is in the repo**, so every run sees the same contract and its history.
- **Separation of duties**— writer and reviewer are different runs with different
  tokens; only the writer can change code, only humans can merge.
- **Everything is audited.** Each implement/review run streams secret-scrubbed
  OTLP events— and its [Anthropic cost](observability.md#per-run-cost)— to Elastic,
  so spec-driven work is fully attributable per feature, branch, and personality.
- **Bypass-permissions stays safe** because the agent runs
  [fully contained](yolo-mode.md)— the spec loop never lowers the sandbox boundary.
