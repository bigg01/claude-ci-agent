# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> ⚠️ Pre-1.0 alpha — anything may change between releases.

## [Unreleased]

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

[Unreleased]: https://github.com/bigg01/claude-ci-agent/compare/v0.1.0-alpha.4...HEAD
[0.1.0-alpha.4]: https://github.com/bigg01/claude-ci-agent/compare/v0.1.0-alpha.3...v0.1.0-alpha.4
[0.1.0-alpha.3]: https://github.com/bigg01/claude-ci-agent/compare/v0.1.0-alpha.2...v0.1.0-alpha.3
[0.1.0-alpha.2]: https://github.com/bigg01/claude-ci-agent/compare/v0.1.0-alpha.1...v0.1.0-alpha.2
[0.1.0-alpha.1]: https://github.com/bigg01/claude-ci-agent/releases/tag/v0.1.0-alpha.1
