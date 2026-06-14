---
icon: lucide/ship-wheel
---

# Kubernetes deployment (Helm)

The [`deploy/helm/claude-ci-agent`](https://github.com/bigg01/claude-ci-agent/tree/main/deploy/helm/claude-ci-agent)
chart deploys the agent and its [per-team OTel Collector](team-routing.md) to
Kubernetes— one template set, portable across **AKS** and **OpenShift**, with
optional **OpenBao** secret injection and **cert-manager** TLS.

```sh
# AKS — the image carries a non-root UID
helm install ci ./deploy/helm/claude-ci-agent -f deploy/helm/claude-ci-agent/values-aks.yaml \
  --set team=sre-payments --set secrets.existingSecret=claude-secrets

# OpenShift — the SCC injects the UID
helm install ci ./deploy/helm/claude-ci-agent -f deploy/helm/claude-ci-agent/values-ocp.yaml \
  --set team=sre-payments --set openbao.enabled=true
```

## Install from a release

The chart is published with every `v*` release— both as a `.tgz` attached to the
[GitHub Release](https://github.com/bigg01/claude-ci-agent/releases) and as an OCI
artifact in GHCR. You don't need to clone the repo:

```sh
# From the OCI registry (version = the release tag without the leading "v")
helm install ci oci://ghcr.io/bigg01/charts/claude-ci-agent --version 0.1.0-alpha.6

# …or from the .tgz attached to the release
helm install ci https://github.com/bigg01/claude-ci-agent/releases/download/v0.1.0-alpha.6/claude-ci-agent-0.1.0-alpha.6.tgz
```

The chart's `appVersion` pins the matching agent image tag automatically, so the
chart and the container image always move together.

## AKS vs OpenShift— the small differences

One chart; the overlays carry the few platform-specific values:

| Concern | AKS | OpenShift |
| --- | --- | --- |
| Pod UID/GID | `runAsUser: 1001`, `runAsGroup: 0`, `fsGroup: 0` | **nulled**— restricted-v2 SCC injects an allocated UID (a hardcoded one is rejected) |
| External exposure | `Ingress` | `Route` (`route.openshift.io/v1`) |
| `runAsNonRoot` + seccomp `RuntimeDefault` | ✓ | ✓ |
| NetworkPolicy engine | Azure NPM / Calico / Cilium | OVN-Kubernetes |

Null securityContext fields are omitted from the rendered manifest, so the SCC is
free to assign them on OCP. The chart also guards misuse— `route.enabled` on AKS
(or `ingress.enabled` on OCP) fails the render with a clear message.

## OpenBao secret injection

`openbao.enabled=true` adds the OpenBao/Vault **Agent Injector** annotations to the
agent pod. The pod's **ServiceAccount** authenticates via OpenBao's **Kubernetes
auth**— no static secret lives in the chart— and the injector renders the KV v2
secret into `/vault/secrets/env`, which the agent sources before it runs. This is
the in-cluster sibling of the [CI OpenBao addon](secrets-openbao.md)'s OIDC flow:
identity, not a stored token.

Set `openbao.keys` for which fields to inject (default `ANTHROPIC_API_KEY`,
`GIT_PUSH_TOKEN`). Without OpenBao, point `secrets.existingSecret` at a Secret
holding `ANTHROPIC_API_KEY`.

## cert-manager TLS

`certManager.enabled=true` issues a serving certificate (from your
`certManager.issuerRef`) for the collector's OTLP endpoint and turns on receiver
TLS— so the agent exports OTLP over **https** to the in-cluster service DNS (a SAN
on the cert). Add more SANs via `certManager.extraDnsNames`. With TLS off, OTLP is
plaintext on the in-cluster network only.

!!! note "Identity and TLS, not stored secrets"

    Both integrations follow the project's posture: OpenBao gives the pod an
    *identity* (its ServiceAccount) rather than a baked-in token, and cert-manager
    *issues and rotates* the collector's certificate rather than shipping a static
    one. See the chart [README](https://github.com/bigg01/claude-ci-agent/blob/main/deploy/helm/claude-ci-agent/README.md).
