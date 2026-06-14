# CLAUDE.MD — consuming project guide (claude-ci-agent example)

This is a small, self-contained project that demonstrates the
[claude-ci-agent](https://github.com/bigg01/claude-ci-agent) **spec-driven loop**
on GitLab. The agent implements the feature described in
[`spec/feature01.md`](spec/feature01.md); a read-only advisor grades the result
against that same spec. This file is the coding contract both sides follow— keep
it short and concrete so the advisor can hold the agent to it.

## What you are working on

A single-file Python CLI that fetches IP / network config from a URL and
pretty-prints it. The spec in [`spec/feature01.md`](spec/feature01.md) is the
source of truth— satisfy **every** acceptance criterion and implement **nothing**
listed under "Out of scope".

## Tech stack & layout

* **Language:** Python 3.10+.
* **Runner / deps:** [uv](https://docs.astral.sh/uv/) with inline
  [PEP 723](https://peps.python.org/pep-0723/) metadata in the script header— so
  `uv run ip_scraper.py` works with no separate install step. Do **not** add a
  `requirements.txt` or a hand-managed virtualenv.
* **HTTP client:** `httpx` (sync). **No third-party dependencies beyond `httpx`**
  without an explicit human directive.
* **Files:** the script (e.g. `ip_scraper.py`), its test (e.g. `test_ip_scraper.py`),
  and a Python `.gitignore`. Keep the tree flat— this is a demo, not a package.

## Coding standards

* **Explicit error paths.** Timeouts, network failures, and invalid JSON must
  print a clear, single-line error and exit **non-zero**— never surface a Python
  traceback to the user.
* **Type hints** on public functions; prefer the standard library (`argparse`,
  `json`, `sys`) over new dependencies.
* **Tests are part of the change.** Cover a success path and a failure path with
  the network **mocked** (no real HTTP in tests). Run them with `uv run pytest`.
* **Dependency minimization.** Reach for the stdlib first; justify any new import.

## Git & commits

* Make **atomic** commits with conventional-commit messages
  (`feat: …`, `fix: …`, `test: …`, `chore: …`).
* The agent works on its **own branch** and opens a **new merge request**— it
  never pushes to the default branch. The advisor only reviews; it never mutates,
  commits, or pushes.

## Telemetry (inherited from the component)

Runs are OTel-instrumented— every tool call and git mutation is scrubbed and
streamed to the collector. Don't dump large raw buffers (e.g. thousands of log
lines) to stdout; it bloats the audit trail for no benefit.

## Communication style

When writing PR/MR text, commit bodies, or comments, use the long em-dash (`—`)
for asides and mid-sentence breaks rather than a spaced hyphen.
