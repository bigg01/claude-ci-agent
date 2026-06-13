# claude-ci-agent Helm chart

Deploys the Claude CI agent and its per-team OTel Collector to Kubernetes,
portable across **AKS** and **OpenShift (OCP)**, with optional **OpenBao** secret
injection and **cert-manager** TLS.

```sh
# AKS (image carries a non-root UID)
helm install ci ./deploy/helm/claude-ci-agent \
  -f deploy/helm/claude-ci-agent/values-aks.yaml \
  --set team=sre-payments --set secrets.existingSecret=claude-secrets

# OpenShift (SCC injects the UID — runAsUser is nulled)
helm install ci ./deploy/helm/claude-ci-agent \
  -f deploy/helm/claude-ci-agent/values-ocp.yaml \
  --set team=sre-payments --set openbao.enabled=true
```

## AKS vs OpenShift — the small differences

The chart is one template set; only a few values differ, captured in the overlays:

| Concern | AKS (`values-aks.yaml`) | OpenShift (`values-ocp.yaml`) |
| --- | --- | --- |
| Pod UID/GID | `runAsUser: 1001`, `runAsGroup: 0`, `fsGroup: 0` | **nulled** — restricted-v2 SCC injects an allocated UID; a hardcoded UID is rejected |
| External exposure | `Ingress` | `Route` (`route.openshift.io/v1`) |
| `runAsNonRoot` + seccomp `RuntimeDefault` | same | same |
| NetworkPolicy | same (Azure NPM/Calico/Cilium) | same (OVN-Kubernetes) |

Null securityContext fields are omitted from the rendered manifest, so the SCC is
free to assign them on OCP.

## OpenBao (Vault-compatible)

`openbao.enabled=true` adds the OpenBao/Vault **Agent Injector** annotations to the
agent pod. The pod's **ServiceAccount** authenticates via OpenBao's **Kubernetes
auth** (no static secret in the chart); the injector renders the KV v2 secret into
`/vault/secrets/env`, which the agent sources before running. Requires the injector
installed in-cluster and an OpenBao role bound to this chart's ServiceAccount:

```sh
bao write auth/kubernetes/role/claude-ci-agent \
  bound_service_account_names="$(helm template ci . | yq '...serviceAccountName')" \
  bound_service_account_namespaces=<ns> \
  policies=claude-ci-agent ttl=15m
```

Keys to inject are `openbao.keys` (default `ANTHROPIC_API_KEY`, `GIT_PUSH_TOKEN`).
Without OpenBao, set `secrets.existingSecret` to a Secret holding `ANTHROPIC_API_KEY`.

## cert-manager TLS

`certManager.enabled=true` issues a serving certificate (from
`certManager.issuerRef`) for the collector's OTLP endpoint and turns on receiver
TLS, so the agent exports OTLP over **https** to the in-cluster service DNS. The
cert's SANs include the collector Service FQDN; add more via
`certManager.extraDnsNames`.

## Per-team

`team` sets `OTEL_TEAM`, naming the collector and its indices
`claude-agent-<team>-*` — see the [team-routing](../../addons/team-routing) addon
for the topology and RBAC.
