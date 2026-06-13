---
icon: lucide/key-round
---

# Secrets via OpenBao (optional)

By default the pipelines read their secrets from native CI/CD variables. As an
**optional addon**, they can instead pull secrets from an
[OpenBao](https://openbao.org) endpoint— the Vault-compatible, open-source
secrets manager.

The job authenticates with **its own short-lived OIDC/JWT**, audience-scoped to
your OpenBao server— no static OpenBao token is ever stored in CI, preserving the
[zero-credential](ci-versions.md) posture.

## How it works

```text
CI job ──(OIDC/JWT, aud=BAO_AUDIENCE)──▶ OpenBao auth/jwt/login ──▶ client token
client token ──▶ KV v2 read (BAO_SECRET_PATH) ──▶ bao.env (0600) ──▶ sourced, then deleted
```

The addon lives at [`addons/openbao/`](https://github.com/)— `fetch-secrets.sh`
does the exchange and the `README.md` covers the one-time OpenBao policy and JWT
role setup for both GitLab and GitHub.

## Enabling it

It is a **no-op unless `BAO_ADDR` is set**. To turn it on, set these CI variables
(GitLab CI/CD variables, or GitHub repo/org **variables**):

| Variable | Example |
| --- | --- |
| `BAO_ADDR` | `https://openbao.example.com` |
| `BAO_ROLE` | `claude-ci-agent` |
| `BAO_SECRET_PATH` | `secret/data/claude-ci-agent` |
| `BAO_AUDIENCE` | `https://openbao.example.com` (must match the role's `bound_audiences`) |

Store the pipeline's secrets— `ANTHROPIC_API_KEY`, `ELASTIC_OTLP_ENDPOINT`,
`ELASTIC_OTLP_AUTHORIZATION`, and `GIT_PUSH_TOKEN`— at `BAO_SECRET_PATH`. When
enabled they override the (empty) native placeholders for the rest of the job.

!!! note "Identity, not a token"

    GitLab mints the JWT via an `id_tokens` block; GitHub mints it from the
    Actions OIDC provider (`permissions: id-token: write`). Neither platform
    stores a long-lived OpenBao credential.
