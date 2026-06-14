---
description: Run the locally-checkable CI gates (pytest, markdown lint, component YAML, docs build) before opening a PR.
allowed-tools: Bash(make:*), Bash(uv:*), Bash(npx:*), Bash(python3:*), Bash(git:*), Read
---

Mirror the `.github/workflows/ci.yml` gates that can run locally, so a PR isn't
the first place you discover a break. The secret-scan and vuln-scan gates need the
CI environment — skip those and say so.

## Context

- Changed files vs `main`: !`git diff --name-only main...HEAD 2>/dev/null || git status -s`

## Run, in order, and report each result

1. **Unit tests + config validation** — `make test` (runs `uv run pytest`). This
   covers `tests/test_config.py` (validates the component/action/Containerfile) and
   `tests/test_emit_cost.py`.
2. **Markdown lint** — only on changed Markdown files:
   `npx --yes markdownlint-cli2 <changed .md files>`. If none changed, skip.
3. **Component YAML parses** —
   `python3 -c "import yaml; list(yaml.safe_load_all(open('templates/claude-agent.yml'))); print('component OK')"`
   and the example: `python3 -c "import yaml; yaml.safe_load(open('examples/gitlab/claude-ci-agent-test/.gitlab-ci.yml')); print('example OK')"`.
4. **Docs build** (only if any `docs/**` or `*.md` changed) — `make docs-build`.

## Report

A short pass/fail table for each gate. On failure, show the actionable error lines
(not the full log) and stop before suggesting a fix unless asked. Remind that
`secret-scan` (gitleaks) and `vuln-scan` (Trivy) only run in CI.
