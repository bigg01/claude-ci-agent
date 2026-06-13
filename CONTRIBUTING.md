# Contributing

Thanks for your interest in improving **claude-ci-agent**! This project is
developed on GitHub (GitLab is a read-only mirror). Contributions of all kinds—
bug reports, docs, features— are welcome.

> Status: early **alpha**. Interfaces, config keys, and image paths may change.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python environment & packaging
- [Podman](https://podman.io/) — rootless container builds (not Docker)

## Set up

```bash
git clone https://github.com/bigg01/claude-ci-agent.git
cd claude-ci-agent
make install          # sync the uv environment (incl. Zensical)
```

## Make your change

- Keep changes focused and match the surrounding style.
- Update the docs under `docs/` when behaviour changes, and add a note to
  [`CHANGELOG.md`](CHANGELOG.md) under **Unreleased**.
- Add or update tests for code changes.

## Run the quality gates locally

The same gates run in CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml))
and **must pass** before a PR can merge:

```bash
make test                       # pytest + coverage floor (>= 85%)
npx --yes markdownlint-cli2     # markdown lint (docs + README)
make docs                       # docs build must be clean
# secret scan (gitleaks) and dependency scan (Trivy) also run in CI
```

For container/stack changes:

```bash
make test-e2e                   # build image + sandbox smoke test
make ci-local                   # full telemetry path on the local stack
```

## Open a pull request

`main` is **protected** — all changes land via pull request, and CI must be green.

1. Branch from `main`: `git checkout -b feat/short-description`.
2. Use [Conventional Commits](https://www.conventionalcommits.org/) for messages
   (`feat:`, `fix:`, `docs:`, `ci:`, `chore:` …).
3. Push and open a PR. Anyone can open one — fork the repo if you don't have write
   access.
4. Ensure all status checks pass; address review feedback.

By contributing you agree your work is licensed under the repository's
[LICENSE](LICENSE) and that you follow the [Code of Conduct](CODE_OF_CONDUCT.md).

Questions? See [SUPPORT.md](SUPPORT.md).
