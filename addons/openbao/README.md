# OpenBao secrets addon (optional)

Fetch the pipeline's secrets from an [OpenBao](https://openbao.org) endpoint
(the Vault-compatible, open-source secrets manager) instead of storing them as
native CI/CD secrets.

The CI job authenticates to OpenBao with **its own OIDC/JWT identity** — no
static OpenBao token lives in CI — then reads a KV v2 path. This keeps the
[zero-credential](../../CLAUDE.MD) posture: the only thing the job presents is a
short-lived, audience-scoped JWT it mints at run time.

**Opt-in:** the addon is a no-op unless `BAO_ADDR` is set. With it unset, the
pipelines fall back to native CI secrets exactly as before.

## What it does

1. `fetch-secrets.sh` POSTs the CI JWT to `auth/<mount>/login` → receives a
   short-lived OpenBao client token.
2. Reads the KV v2 secret at `BAO_SECRET_PATH` → writes each field to a `0600`
   `bao.env` dotenv (`export KEY='value'`).
3. The job sources `bao.env`, then deletes it. Sourced values override the
   (empty) job-level placeholders for the rest of the shell.

Store these keys in OpenBao so they land in the job environment: `ANTHROPIC_API_KEY`,
`ELASTIC_OTLP_ENDPOINT`, `ELASTIC_OTLP_AUTHORIZATION`, and (GitLab agent) `GIT_PUSH_TOKEN`.

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `BAO_ADDR` | to enable | OpenBao base URL, e.g. `https://openbao.example.com` |
| `BAO_ROLE` | yes | JWT auth role to assume |
| `BAO_SECRET_PATH` | yes | KV v2 **data** path, e.g. `secret/data/claude-ci-agent` |
| `BAO_AUDIENCE` | yes | Audience claim the JWT is minted with; must match the role's `bound_audiences` |
| `BAO_AUTH_PATH` | no | JWT auth mount (default `jwt`) |
| `BAO_JWT` | injected | The CI OIDC/JWT — set by the pipeline, not by hand |

## One-time OpenBao setup

```sh
# KV v2 + the secrets the pipeline expects
bao secrets enable -path=secret kv-v2
bao kv put secret/claude-ci-agent \
  ANTHROPIC_API_KEY=sk-ant-... \
  ELASTIC_OTLP_ENDPOINT=https://elastic.example.com:443 \
  ELASTIC_OTLP_AUTHORIZATION="ApiKey ..." \
  GIT_PUSH_TOKEN=glpat-...

# Read-only policy scoped to that one path
bao policy write claude-ci-agent - <<'EOF'
path "secret/data/claude-ci-agent" { capabilities = ["read"] }
EOF

# JWT auth, wired to the CI issuer
bao auth enable jwt
```

=== "GitLab"

    ```sh
    bao write auth/jwt/config \
      oidc_discovery_url="https://gitlab.com" \
      bound_issuer="https://gitlab.com"

    bao write auth/jwt/role/claude-ci-agent \
      role_type="jwt" user_claim="project_id" \
      bound_audiences="https://openbao.example.com" \
      bound_claims_type="glob" bound_claims='{"project_path":"my-group/*"}' \
      token_policies="claude-ci-agent" token_ttl="10m"
    ```

    The pipeline mints the JWT via an `id_tokens` block; set the CI/CD variables
    `BAO_ADDR`, `BAO_ROLE`, `BAO_SECRET_PATH`, and `BAO_AUDIENCE`.

=== "GitHub"

    ```sh
    bao write auth/jwt/config \
      oidc_discovery_url="https://token.actions.githubusercontent.com" \
      bound_issuer="https://token.actions.githubusercontent.com"

    bao write auth/jwt/role/claude-ci-agent \
      role_type="jwt" user_claim="repository" \
      bound_audiences="https://openbao.example.com" \
      bound_claims_type="glob" bound_claims='{"repository":"my-org/*"}' \
      token_policies="claude-ci-agent" token_ttl="10m"
    ```

    The workflow mints the JWT from the Actions OIDC provider (needs
    `permissions: id-token: write`); set the repo/org variables `BAO_ADDR`,
    `BAO_ROLE`, `BAO_SECRET_PATH`, and `BAO_AUDIENCE`.

## Manual test

```sh
BAO_ADDR=https://openbao.example.com \
BAO_ROLE=claude-ci-agent \
BAO_SECRET_PATH=secret/data/claude-ci-agent \
BAO_JWT="$(cat token.jwt)" \
  sh addons/openbao/fetch-secrets.sh
. ./bao.env && rm -f bao.env
```
