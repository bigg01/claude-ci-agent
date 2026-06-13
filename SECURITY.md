# Security Policy

> Early **alpha** — not recommended for production use yet.

## Supported versions

Only the latest `0.1.0-alpha.*` prerelease receives fixes. Pin to a released tag
and a published image digest for reproducibility.

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

- Preferred: open a private
  [GitHub Security Advisory](https://github.com/bigg01/claude-ci-agent/security/advisories/new).
- Or email the maintainer at <o.guggenbuehl@gmail.com>.

Include affected version/commit, impact, and reproduction steps. You'll get an
acknowledgement as soon as possible; please allow reasonable time for a fix before
public disclosure.

## Notes

- The agent is designed to run **fully contained** (rootless, non-root, zero
  ambient credentials, secret-scrubbed telemetry) — see
  [Sandboxing & YOLO Mode](https://bigg01.containerize.ch/claude-ci-agent/yolo-mode/).
- CI runs secret scanning (gitleaks) and dependency/image vulnerability scanning
  (Trivy); never commit real credentials — the agent expects keys via CI secrets.
