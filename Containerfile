# Containerfile — rootless, unprivileged Podman workspace for the Claude CI agent
#
# Derived from input/gemini.md (the "Unprivileged Podman Workspace" blueprint) and
# reconciled with CLAUDE.MD: rootless Podman base, Node for the Claude Code CLI,
# OpenShift arbitrary-UID compatibility (group-writable HOME/npm prefix).
#
# Build:  podman build -t app-test -f Containerfile .
FROM quay.io/podman/stable:latest

# 1. Node.js + npm are required to run the Claude Code CLI; python3 backs the
#    OTel cost emitter (otel/emit_cost.py, standard library only); jq + curl back
#    the advisor/agent personalities (MR/PR notes, branch+MR/PR creation) used by
#    the GitLab component and GitHub workflow.
RUN dnf install -y nodejs npm git python3 jq curl && dnf clean all

# 2. The image must run as a non-root user on BOTH platforms:
#    - OpenShift assigns an arbitrary, non-root UID at runtime (e.g. 1000740000)
#      that is NOT in /etc/passwd and whose primary group is root (GID 0).
#    - AKS / vanilla Kubernetes with the "restricted" Pod Security Standard
#      requires runAsNonRoot, so the image itself must default to a non-root UID.
#    Both cases are satisfied by making everything the agent writes to group-
#    writable (GID 0) and shipping a non-root default user.
ENV NPM_CONFIG_PREFIX=/opt/npm-global \
    PATH=/opt/npm-global/bin:$PATH \
    HOME=/opt/agent-home

RUN mkdir -p /opt/npm-global /opt/agent-home /workspace \
    && npm install -g @anthropic-ai/claude-code \
    && chgrp -R 0 /opt/npm-global /opt/agent-home /workspace \
    && chmod -R g=u /opt/npm-global /opt/agent-home /workspace

# 3. Bake the CI helper assets into the image at a stable path. The GitLab
#    component is `include:`d by OTHER projects that do NOT have this repo checked
#    out, so it cannot reference otel/ or addons/ relative to the working tree —
#    it references these baked copies instead. The GitHub workflow runs in this
#    repo and can use either path. World-readable so an arbitrary OpenShift UID
#    can still read them.
COPY otel/emit_cost.py otel/otel-collector-config.yaml /opt/claude-ci/
COPY addons/openbao/fetch-secrets.sh /opt/claude-ci/
RUN chmod -R a+rX /opt/claude-ci

# 4. Verify Podman is present and the toolchain installed (build-time smoke test).
RUN podman --version && node --version && claude --version

WORKDIR /workspace

# 5. Default to a non-root UID with primary group root (GID 0). AKS uses this UID
#    directly; OpenShift overrides it with its allocated UID — group-writable
#    paths above keep both working.
USER 1001:0
