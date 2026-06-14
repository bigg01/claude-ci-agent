---
description: Cut a new release — bump every version pin, update the CHANGELOG, open the release PR, and tag after merge.
argument-hint: "[next version, e.g. 0.1.0-alpha.9]"
allowed-tools: Bash(git:*), Bash(gh:*), Bash(grep:*), Bash(sed:*), Bash(python3:*), Read, Edit
---

You are cutting release **v$ARGUMENTS** of claude-ci-agent. If `$ARGUMENTS` is
empty, infer the next version from the latest tag and ask the user to confirm.

## Context

- Current version pins in the tree:
  !`git grep -l -E "0\.1\.0-alpha\.[0-9]+" -- ':!CHANGELOG.md' || true`
- Latest tag: !`git describe --tags --abbrev=0 2>/dev/null || echo none`
- Current branch / status: !`git status -sb | head -20`
- CHANGELOG `[Unreleased]` section: @CHANGELOG.md

## How releases work here (no helm chart anymore)

A release is **pin bumps + CHANGELOG + a `vX` tag**. Pushing the tag triggers two
things automatically — do NOT do them by hand:
- `.github/workflows/claude-agent.yml` `build-image` publishes the agent image at
  `:<version>`, `:latest`, and `:<sha>`.
- The GitLab mirror's `.gitlab-ci.yml` publishes the component to the CI/CD Catalog
  on tag sync.

## Steps

1. **Branch.** From an up-to-date `main`, create `release/v<version>`. If the repo
   is already on a `release/*` branch with the bump in progress, continue on it.
2. **Bump every pin** from the old version to `<version>` across all files found by
   the grep above (currently: `action.yml`, `templates/claude-agent.yml`,
   `docs/ci-versions.md`, `docs/spec-driven.md`, and the
   `examples/gitlab/claude-ci-agent-test/` files). Use a single `sed -i` over that
   file list, then re-grep to prove no stale `alpha.<old>` refs remain outside
   `CHANGELOG.md` history.
3. **CHANGELOG.** Rename `## [Unreleased]` → `## [<version>] — <today's date>`
   (keep its Added/Changed/Fixed/Docs entries), add a fresh empty `## [Unreleased]`
   above it, and add a `### Changed` note "Pinned component/action/docs to
   `<version>`." Update the compare-link footer: point `[Unreleased]` at
   `v<version>...HEAD` and add a `[<version>]: …compare/v<old>...v<version>` line.
   Use today's date from the environment, not a guess.
4. **Commit** as `release: v<version>` (end the message with the repo's
   `Co-Authored-By: Claude …` trailer), **push**, and **open a PR** to `main` with
   `gh pr create`, summarizing the changes and the local test results.
5. **Wait for CI**, report check status, and STOP. The tag is the irreversible,
   outward-facing step — only push it after the PR is merged, and confirm with the
   user first (or merge with `--admin` only if they explicitly approve):
   ```sh
   git checkout main && git pull --ff-only
   git tag -a v<version> -m "v<version>" && git push origin v<version>
   ```
6. After tagging, confirm the `claude-agent` `build-image` run succeeded so the
   `:<version>` image pin actually resolves.

Be precise about the version string; a typo'd pin ships a broken component.
