#!/usr/bin/env sh
# ===========================================================================
# OPTIONAL ADDON — fetch CI secrets from an OpenBao (Vault-compatible) endpoint.
#
# The CI job's own OIDC/JWT identity authenticates to OpenBao via the JWT auth
# method, so NO static OpenBao token is stored in CI — consistent with
# CLAUDE.MD's zero-credential stance. Secrets are read from a KV v2 path and
# written to a 0600 dotenv file (export KEY='value') that the caller sources
# and then deletes.
#
# This addon is OPT-IN: when BAO_ADDR is unset it prints a notice and exits 0,
# so the pipeline falls back to native CI secrets unchanged.
#
# Required when enabled:
#   BAO_ADDR         OpenBao base URL (e.g. https://openbao.example.com)
#   BAO_ROLE         JWT auth role to assume
#   BAO_JWT          CI-issued OIDC/JWT (GitLab id_token / GitHub OIDC)
#   BAO_SECRET_PATH  KV v2 *data* path (e.g. secret/data/claude-ci-agent)
# Optional:
#   BAO_AUTH_PATH    JWT auth mount (default: jwt)
#   BAO_ENV_FILE     dotenv output path (default: ./bao.env)
#
# Usage in a CI before_script (POSIX shell):
#   sh addons/openbao/fetch-secrets.sh
#   [ -f bao.env ] && { set -a; . ./bao.env; set +a; rm -f bao.env; }
# ===========================================================================
set -eu

if [ -z "${BAO_ADDR:-}" ]; then
  echo "OpenBao addon: BAO_ADDR unset — skipping (using native CI secrets)." >&2
  exit 0
fi

: "${BAO_ROLE:?OpenBao addon: BAO_ROLE required when BAO_ADDR is set}"
: "${BAO_JWT:?OpenBao addon: BAO_JWT required when BAO_ADDR is set}"
: "${BAO_SECRET_PATH:?OpenBao addon: BAO_SECRET_PATH required when BAO_ADDR is set}"
BAO_AUTH_PATH="${BAO_AUTH_PATH:-jwt}"
BAO_ENV_FILE="${BAO_ENV_FILE:-./bao.env}"
addr="${BAO_ADDR%/}"

# 1. Exchange the CI JWT for a short-lived OpenBao client token.
login_resp="$(curl -sS --fail \
  --request POST \
  --data "{\"role\":\"${BAO_ROLE}\",\"jwt\":\"${BAO_JWT}\"}" \
  "${addr}/v1/auth/${BAO_AUTH_PATH}/login")"

client_token="$(printf '%s' "$login_resp" \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["auth"]["client_token"])')"

# 2. Read the KV v2 secret and emit shell-safe `export KEY=VALUE` lines. Writing
#    happens under a tight umask so the dotenv file is never world-readable.
umask 077
secret_resp="$(curl -sS --fail \
  --header "X-Vault-Token: ${client_token}" \
  "${addr}/v1/${BAO_SECRET_PATH}")"

printf '%s' "$secret_resp" | python3 -c '
import sys, json, shlex
data = json.load(sys.stdin)["data"]["data"]   # KV v2 nests the payload under data.data
with open(sys.argv[1], "w") as fh:
    for key, value in data.items():
        fh.write("export %s=%s\n" % (key, shlex.quote(str(value))))
' "$BAO_ENV_FILE"

count="$(grep -c '^export ' "$BAO_ENV_FILE" 2>/dev/null || echo 0)"
echo "OpenBao addon: loaded ${count} secret(s) from ${BAO_SECRET_PATH}." >&2
