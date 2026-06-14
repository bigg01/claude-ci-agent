---
icon: lucide/shield-check
---

# Sandboxing & YOLO Mode

"YOLO mode"— running the agent with `--dangerously-skip-permissions` so it
executes commands without per-action approval— is normally risky because the
agent can run arbitrary code. The usual mitigation is to wrap it in a dedicated
sandbox runtime (e.g. Anthropic's sandbox-runtime for bash/filesystem isolation,
or a vendor GPU/container sandbox such as NVIDIA's).

!!! success "We don't need that extra layer— the agent already runs fully contained"

    The isolation those sandboxes provide is already true of our execution
    environment, so a bolt-on sandbox would be *redundant* isolation, not new
    isolation.

## Why the containment already exists

The sandbox is **not something this project bolts on** — it is provided by
*where the job runs*. The GitLab Runner executes the pipeline job **inside the
`claude-agent` image as a container** (its container/Kubernetes executor), and
`claude` runs as that container's process. On a self-hosted/private runner
deployed on **OpenShift**, that job pod is admitted under the `restricted-v2`
SCC — arbitrary non-root UID, `allowPrivilegeEscalation: false`, dropped
capabilities — so the platform *itself* enforces the rootless, unprivileged
boundary. Either way the containment is a property of the runner, not of a
wrapper we add around Claude.

- **Rootless, unprivileged container.** `claude` runs **directly in** its
  container — the [`claude-agent` image](architecture.md) — as a non-root user
  with an arbitrary, non-root UID and no privilege escalation. It is *not* wrapped
  in a nested `podman run`; the container *is* the sandbox. What runs that
  container varies by platform — rootless **Podman** on a CI runner, or the
  **Kubernetes CRI** (e.g. CRI-O) on a self-hosted runner on OpenShift — but the
  rootless, unprivileged boundary is identical either way. The blast radius of any
  command is the throwaway container, not a host. (Nested Podman is used only by
  the agent itself, to build/test the app under review — see
  [Architecture](architecture.md).)
- **Ephemeral CI workspace.** Each run starts from a fresh image and is destroyed
  afterwards. There is no persistent state for a bad command to corrupt.
- **Zero-credential environment.** No global Git credentials, SSH keys, or
  production tokens are present. The agent cannot reach the host OS environment,
  and an escaped secret has nothing to steal. GitHub Actions runs use only
  workflow-scoped `GITHUB_TOKEN`/secrets.
- **Secret-scrubbed, fully audited.** Every command, output, and git mutation is
  streamed as OTLP events through the OTel Collector sidecar (with secret
  scrubbing) to Elastic— so even "skip approvals" runs remain reviewable.

In other words, the security boundary that a bolt-on sandbox would add is
*already* the boundary we run inside. YOLO mode here means **"skip the prompts,"**
not **"skip the containment."**

## Example— a YOLO-mode run

A headless run in the sandbox with bypass-permissions on. The agent does its work
with no approval prompts— and when it reaches for something the sandbox forbids,
the **container**, not a prompt, stops it:

```console
$ podman run --rm -e ANTHROPIC_API_KEY app-test \
    claude --dangerously-skip-permissions \
      -p "Build the project, run the tests, then install 'cowsay' to celebrate."

● Building, testing, then attempting the install.
  $ podman build -t app-test .          → ok
  $ npm test                            → 12 passed
  $ dnf install -y cowsay
    Error: This command has to be run with superuser privileges
           (under the root user on most systems).
● I can't install system packages here— this is a non-root, rootless Podman
  sandbox. Build and tests passed; skipping the install.
```

No approval prompt appeared (that is YOLO mode), yet the privileged action was
**denied by the runtime**— precisely the boundary a bolt-on sandbox would add,
already enforced. The agent adapts and reports that it couldn't install.

!!! note "This is verified automatically— not just asserted"

    The e2e suite's **Sandbox containment** stage
    ([`tests/e2e.sh`](https://github.com/bigg01/claude-ci-agent/blob/main/tests/e2e.sh))
    runs this exact scenario on every build: inside the image it attempts a package
    install, a write to a system path, and a privilege escalation, and **fails the
    build unless all three are denied**. With `ANTHROPIC_API_KEY` set it also has
    Claude itself try to install software and asserts the sandbox blocks it:

    ```text
    ✓ install/escalation denied inside the rootless sandbox — CONTAINED uid=1001
    ✓ Claude tried to install software and was blocked by the sandbox
    ```

## How our solution compares

Both the Anthropic and NVIDIA sandboxes exist to add an isolation boundary
*around* an agent that would otherwise run on a trusted host. Our agent never runs
on a trusted host in the first place— it runs inside a rootless, unprivileged,
ephemeral CI container— so the same boundary is already present.

| Capability | Our solution— rootless CI container (e.g. on an OpenShift GitLab Runner) | Anthropic sandbox (sandbox-runtime) | NVIDIA sandbox (container / microVM GPU isolation) |
| --- | --- | --- | --- |
| **Isolation mechanism** | OS-level container (namespaces + cgroups), rootless | OS primitives wrapping a process (bubblewrap on Linux, Seatbelt on macOS) | Hardened container / microVM around the workload |
| **Primary purpose** | Run untrusted CI workloads safely | Confine a single agent's bash/file/network access on a dev host | Isolate GPU compute workloads from host and each other |
| **Filesystem isolation** | ✅ Container rootfs only; host FS not mounted | ✅ Allowlisted paths | ✅ Container/VM scoped |
| **Network isolation** | ✅ CI network policy; no host network | ✅ Egress allowlist | ✅ Policy dependent |
| **Privilege model** | ✅ Rootless, non-root arbitrary UID, no escalation | ⚠️ Inherits the host user's privileges | ✅ Reduced / VM-isolated |
| **Credential exposure** | ✅ Zero-credential; host env unreachable | ⚠️ Whatever the host user can see | ⚠️ Deployment dependent |
| **Ephemerality** | ✅ Fresh image per run, destroyed after | ❌ Persistent dev machine | ⚠️ Deployment dependent |
| **Audit / telemetry** | ✅ Secret-scrubbed OTLP → Elastic | ❌ Not built in | ❌ Not built in |
| **GPU workloads** | ➖ Not needed (no GPU compute here) | ➖ N/A | ✅ Its core use case |
| **Extra setup to adopt** | ✅ None— it *is* the runtime | ❌ Install + configure per host | ❌ Provision GPU sandbox infra |

!!! success "Net result"

    Every isolation property the Anthropic or NVIDIA sandbox would add— process
    confinement, filesystem and network scoping, reduced privilege— is already
    delivered by the rootless CI container, *plus* ephemerality and secret-scrubbed
    auditing that those sandboxes don't provide out of the box. Layering them on top
    is redundant isolation, not new isolation.

> Legend: ✅ provided · ⚠️ partial / depends on deployment · ❌ not provided · ➖ not applicable.

## Enforcement on an OpenShift runner

When the GitLab Runner is self-hosted on **OpenShift**, the containment above is
not aspirational— the cluster's admission controls enforce it on every job pod:

| Control | How OpenShift enforces it |
| --- | --- |
| **Non-root, no privilege escalation** | `restricted-v2` SCC allocates an arbitrary non-root UID and sets `allowPrivilegeEscalation: false` |
| **Dropped capabilities / seccomp** | enforced by the SCC |
| **Network isolation** | OVN-Kubernetes NetworkPolicy |
| **Ephemerality** | a fresh job pod per pipeline run, torn down after |

The image ([`Containerfile`](architecture.md)) ships a non-root default user
(`USER 1001:0`) with group-writable paths, so it runs cleanly under OpenShift's
arbitrary-UID injection without per-platform image changes.

!!! warning "Scope of this justification"

    This justifies enabling bypass-permissions mode for **unattended CI runs**. It
    is **not** a recommendation to run YOLO mode on a developer workstation or any
    host without equivalent containment.
