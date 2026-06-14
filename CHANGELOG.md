# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> ⚠️ Pre-1.0 alpha — anything may change between releases.

## [Unreleased]

## [0.1.0-alpha.8] — 2026-06-14

### Removed
- **Kubernetes/Helm deployment of the agent.** The project now focuses solely on
  **GitLab CI** and **GitHub Actions**. Deleted the `deploy/` tree (Helm chart,
  `agent-job.yaml`, `networkpolicy.yaml`), `docs/kubernetes.md`, the Helm-only
  `release.yml` workflow, the `addons/team-routing/k8s/` manifests, and the K8s
  manifest tests. Releases still publish the sandbox image; they no longer package
  a Helm chart.

### Added
- **`branch_prefix` component input** (default `claude/task-`). The agent's branch
  name is now overridable — the pipeline id is still appended for uniqueness
  (e.g. `claude/task-1234`). Keep it in sync with any advisor `rules:` that match
  on the branch name.
- **`claude-result.json` (and `review.md`) stored as job artifacts.** Both
  component jobs now publish the raw Claude run output — usage, cost, result — with
  `when: always`, so it survives a failed MR post / push and is downloadable from
  the pipeline.

### Changed
- The example's spec-graded `claude-agent-advisor` now **auto-reviews only the
  agent's own MRs** (source branch `claude/task-*`) via a `rules:` `if:` match,
  instead of running on a manual click — keeping it off human-authored MRs and
  non-MR pipelines.
- Reframed the docs (README, architecture, yolo-mode, getting-started, index) so
  the sandbox is described as **the runner-provided job container** — rootless
  Podman on a CI runner, or the Kubernetes CRI on a self-hosted runner on
  **OpenShift** (where the `restricted-v2` SCC enforces the boundary). Dropped the
  AKS deployment target.
- Pinned component/action/example/docs to `0.1.0-alpha.8`.

## [0.1.0-alpha.7] — 2026-06-14

### Changed
- **Reverted the alpha.6 nested-Podman wrapper.** `claude` again runs **directly
  in the job's container** — which *is* the rootless sandbox the GitLab Runner (or
  a private runner on OpenShift) starts from the image. The alpha.6
  `claude_in_sandbox` helper wrapped Claude in a second `podman run`, which
  required nested rootless Podman with `/etc/subuid`/`subgid` ranges that typical
  runners don't grant — so image unpack failed (`no subuid ranges found … lchown:
  invalid argument`) before Claude could start. Nested Podman is now used only
  where it was always needed: the OTel sidecar, and the agent's own app
  build/test. Pinned to `0.1.0-alpha.7`.

### Docs
- Clarified across [architecture](docs/architecture.md), [yolo-mode](docs/yolo-mode.md),
  [spec-driven](docs/spec-driven.md), and [ci-versions](docs/ci-versions.md) that
  the sandbox is **the job container the runner provides** — not a wrapper this
  project adds — and that the runtime is rootless Podman on a CI runner or the
  Kubernetes CRI (CRI-O/containerd) on a private OpenShift/AKS runner. Claude is
  never wrapped in a nested `podman run`.

## [0.1.0-alpha.6] — 2026-06-14

### Changed
- **Claude now runs inside a nested rootless-Podman sandbox.** The GitLab
  component's `claude-advisor`/`claude-agent` jobs no longer exec `claude`
  directly in the job shell — a new `claude_in_sandbox` helper launches it with
  `podman run` in a fresh copy of the pinned sandbox image, mounting only the
  working tree (`$CI_PROJECT_DIR`) and passing secrets/OTel context by name. The
  example's custom advisor uses the same helper.
- Pinned chart/component/action/docs to `0.1.0-alpha.6`.

### Fixed
- Pinned the nested container's process to the checkout owner with
  `--userns=keep-id --user "$(id -u):$(id -g)"` so files Claude writes round-trip
  back owned by the job user — otherwise the agent's `git commit`/`push` and the
  advisor's `review.md` read could fail with permission errors. Verified locally.

## [0.1.0-alpha.5] — 2026-06-14

### Added
- **Runnable GitLab example.** [`examples/gitlab/claude-ci-agent-test/`](examples/gitlab/claude-ci-agent-test/)
  is a copy-paste consuming project (`.gitlab-ci.yml` + `spec/feature01.md`) that
  gates the agent behind a manual click, pins the advisor to a cheaper model, and
  shows a custom advisor job extending the component's hidden `.claude-base`
  template. Linked from both the [CI Versions](docs/ci-versions.md) and
  [Spec-driven](docs/spec-driven.md) docs.

### Fixed
- Example advisor job passed `$[[ inputs.claude_args ]]` from a *consuming*
  project, where component-input interpolation doesn't apply — it reached the
  `claude` CLI verbatim and failed the job. Replaced with a literal flag and
  documented the gotcha.

### Changed
- Pinned chart/component/action/docs to `0.1.0-alpha.5`.

## [0.1.0-alpha.4] — 2026-06-13

### Added
- **GitLab component parity.** [`templates/claude-agent.yml`](templates/claude-agent.yml)
  now ships **both personalities** as jobs, at parity with the GitHub workflow:
  `claude-advisor` (read-only, runs on `merge_request_event`, posts the review as
  an MR note) and `claude-agent` (read-write, runs on a non-empty `$CLAUDE_TASK`,
  opens a new branch + MR). Both add an OTel Collector sidecar (nested Podman),
  per-run cost emission, and the optional OpenBao OIDC secret fetch. New inputs:
  `model`, `token_variable`, `team`, `bao_audience`; `prompt` is now optional.
- Docs: "The whole loop as one `include:`" spec-driven example using the component.

### Changed
- The sandbox image ([`Containerfile`](Containerfile)) now installs `jq` + `curl`
  and **bakes the CI helpers** (`emit_cost.py`, `otel-collector-config.yaml`,
  `fetch-secrets.sh`) into `/opt/claude-ci/`, so the GitLab component works in
  consuming projects that have no checkout of this repo.
- Pinned chart/component/action/docs to `0.1.0-alpha.4`.

## [0.1.0-alpha.3] — 2026-06-13

### Added
- OTel telemetry now tags every run with **`claude.model`** (the model that
  actually served the run) and **`git.commit.sha`** (the commit it produced).
- Community health files: `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SUPPORT`,
  `SECURITY`, and `CODEOWNERS`; README links to the published docs site.
- Docs: GitLab + Jira spec-driven scenario.

### Changed
- `main` is now a protected branch (PR-only, required CI checks).
- Pinned chart/component/action/docs to `0.1.0-alpha.3`.

## [0.1.0-alpha.2] — 2026-06-13

### Added
- CI quality gates in [`.github/workflows/ci.yml`](.github/workflows/ci.yml):
  test coverage floor, markdown lint, secret scan (gitleaks), dependency
  vulnerability scan (Trivy), and a non-blocking image scan that reports to the
  Security tab.
- "Setting the Anthropic API key" documentation for GitHub Actions secrets and
  GitLab CI/CD variables.
- Community health files: `CHANGELOG`, `CONTRIBUTING`, `CODE_OF_CONDUCT`,
  `SUPPORT`, and `CODEOWNERS`.

### Changed
- Pinned the Helm chart, GitLab component, GitHub Action, and docs to
  `0.1.0-alpha.2`.

## [0.1.0-alpha.1] — 2026-06-13

### Added
- Rootless, unprivileged Podman sandbox agent image (`Containerfile`), portable
  across OpenShift and AKS.
- Reusable CI units: GitLab CI/CD component (`templates/`) and GitHub Action
  (`action.yml`), plus event-driven workflows and `.gitlab-ci.yml`.
- Helm chart (`deploy/helm/`) and raw manifests (`deploy/`), hardened for the
  `restricted` Pod Security Standard / OpenShift SCC.
- OpenTelemetry collector configs with secret scrubbing; per-run Anthropic cost
  reporting (`otel/emit_cost.py`).
- Local Podman Compose stack (Elasticsearch + Kibana + OTel Collector) and an
  importable Kibana dashboard.
- pytest suite, end-to-end and local-CI test scripts.
- Zensical documentation site.

[Unreleased]: https://github.com/bigg01/claude-ci-agent/compare/v0.1.0-alpha.8...HEAD
[0.1.0-alpha.8]: https://github.com/bigg01/claude-ci-agent/compare/v0.1.0-alpha.7...v0.1.0-alpha.8
[0.1.0-alpha.7]: https://github.com/bigg01/claude-ci-agent/compare/v0.1.0-alpha.6...v0.1.0-alpha.7
[0.1.0-alpha.6]: https://github.com/bigg01/claude-ci-agent/compare/v0.1.0-alpha.5...v0.1.0-alpha.6
[0.1.0-alpha.5]: https://github.com/bigg01/claude-ci-agent/compare/v0.1.0-alpha.4...v0.1.0-alpha.5
[0.1.0-alpha.4]: https://github.com/bigg01/claude-ci-agent/compare/v0.1.0-alpha.3...v0.1.0-alpha.4
[0.1.0-alpha.3]: https://github.com/bigg01/claude-ci-agent/compare/v0.1.0-alpha.2...v0.1.0-alpha.3
[0.1.0-alpha.2]: https://github.com/bigg01/claude-ci-agent/compare/v0.1.0-alpha.1...v0.1.0-alpha.2
[0.1.0-alpha.1]: https://github.com/bigg01/claude-ci-agent/releases/tag/v0.1.0-alpha.1
