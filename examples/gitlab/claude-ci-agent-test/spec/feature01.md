# spec/feature01.md — IP Config Scraper

## Goal

A lightweight, single-file Python script that fetches IP and network configuration
details from a specified URL (e.g. `https://ifconfig.me/all.json` or
`https://httpbin.org/ip`) and pretty-prints the formatted output to the console.

## Technology stack

- **Language:** Python 3.10+
- **Package manager:** [uv](https://docs.astral.sh/uv/) (by Astral) — use uv's
  script runner with inline [PEP 723](https://peps.python.org/pep-0723/) metadata
  rather than a hand-managed virtualenv.
- **HTTP client:** `httpx` (sync is sufficient for a single URL).

## Acceptance criteria

- [ ] A single script (e.g. `ip_scraper.py`) fetches a target URL, defaulting to a
      reliable JSON IP API.
- [ ] The target URL is overridable via a command-line argument.
- [ ] JSON responses are pretty-printed; non-JSON responses are printed as text.
- [ ] Timeouts, network failures, and invalid JSON are handled gracefully — the
      script prints a clear error and exits non-zero rather than tracebacking.
- [ ] Dependencies are declared inline via PEP 723 metadata so `uv run ip_scraper.py`
      works with no separate install step.
- [ ] A unit test covers both the success path and a failure path (e.g. a timeout
      or invalid JSON), with the network call mocked.

## Out of scope

- Persisting results to a file or database.
- Concurrent/async fetching of multiple URLs.
- Any web server or long-running process.

## Constraints

- Follow CLAUDE.MD coding standards. No third-party dependencies beyond `httpx`.
