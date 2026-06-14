---
description: Inspect a GitLab pipeline/job for the component test project (status + failing-job trace).
argument-hint: "[pipeline ID | job ID | branch name]"
allowed-tools: Bash(curl:*), Bash(glab:*), Bash(python3:*), Bash(jq:*)
---

Debug the GitLab CI run for the component's test project. This is the recurring
loop: a tag sync or manual trigger runs the `claude-agent`/`claude-advisor` jobs
on GitLab, and you need to see why a job failed.

- **Project:** `bigg01/claude-ci-agent-test2` (URL-encoded: `bigg01%2Fclaude-ci-agent-test2`).
- **API base:** `https://gitlab.com/api/v4/projects/bigg01%2Fclaude-ci-agent-test2`

Argument `$ARGUMENTS` may be a pipeline ID, a job ID, or a branch name (default:
the latest pipeline if omitted).

## Procedure

1. Prefer `glab` if it's authenticated (`glab auth status`); otherwise fall back to
   `curl -sS` against the API base above (the project is public for reads).
2. **Resolve the target:**
   - No arg / branch → list recent pipelines: `…/pipelines?ref=<branch>` (or
     `…/pipelines` for the latest), take the newest `id`.
   - Pipeline id → `…/pipelines/<id>/jobs` and print each job's `id name stage status`.
   - Job id → go straight to its trace.
3. **For any failed job**, fetch and show the *relevant* tail of its trace:
   `…/jobs/<job-id>/trace` — surface the actual error lines (the `claude` invocation,
   the OpenBao/sidecar step, the key/`GITLAB_TOKEN` fail-fast message, or the
   git push / MR-create curl), not the whole log.
4. **Diagnose** against what we know about this component: missing/unprotected
   `ANTHROPIC_API_KEY` or `GITLAB_TOKEN`, a runner that can't do nested rootless
   Podman (OTel sidecar), `$[[ inputs.* ]]` used in a *consuming* file (it doesn't
   interpolate there), or a branch-name/`rules:` mismatch.

Parse JSON with `python3 -c` or `jq`. Report: the pipeline status, the per-job
table, and for failures the root-cause lines + the most likely fix.
