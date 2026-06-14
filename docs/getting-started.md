---
icon: lucide/list-checks
---

# Step-by-step guide

This guide takes you from a fresh clone to running the agent in CI and viewing its
telemetry. Each step is self-contained— stop wherever you have what you need.

!!! tip "Prerequisites"

    - [uv](https://docs.astral.sh/uv/)— Python package & environment management
    - [Podman](https://podman.io/)— rootless container builds (not Docker)
    - An `ANTHROPIC_API_KEY` for live agent runs

## Step 1— Clone the repository

```bash
git clone https://github.com/bigg01/claude-ci-agent.git
cd claude-ci-agent
```

## Step 2— Install dependencies

Syncs the Python environment (including Zensical) via uv.

```bash
make install
```

## Step 3— Preview the documentation (optional)

```bash
make serve     # live preview at http://localhost:8000
```

Edit anything under `docs/`; the server live-reloads. Run `make docs-build` to
produce the static site in `site/`.

## Step 4— Build the sandbox image

Builds the rootless, non-root agent image (`app-test`) from the `Containerfile`.

```bash
make build
```

!!! note

    The container engine defaults to Podman. Override with
    `make build CONTAINER_ENGINE=docker` if you must.

## Step 5— Run the end-to-end test locally

Validates configs, builds the image, smoke-tests the toolchain inside the
container, and (if a key is present) does a live agent run.

```bash
make test-e2e                       # full run
SKIP_BUILD=1 make test-e2e          # reuse the image from step 4
ANTHROPIC_API_KEY=… make test-e2e   # also exercise the live agent
```

A green run ends with `✓ e2e passed`.

## Step 6— Wire it into CI

=== "GitLab"

    Reference the bundled [component](ci-versions.md#gitlab-ci-using-the-claude-agent-component)
    from your `.gitlab-ci.yml`:

    ```yaml
    include:
      - component: $CI_SERVER_FQDN/<group>/claude-ci-agent/claude-agent@main
        inputs:
          prompt: "Fix the failing unit tests and commit the change."
    ```

=== "GitHub Actions"

    Use the reusable [action](ci-versions.md#github-actions-using-the-claude-ci-agent-action):

    ```yaml
    jobs:
      agent:
        runs-on: ubuntu-latest
        steps:
          - uses: bigg01/claude-ci-agent@v1
            with:
              prompt: "Fix the failing unit tests and commit the change."
              anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    ```

## Step 7— View telemetry in Elastic

Every command, output, and git mutation is streamed (secret-scrubbed) to Elastic
via the OTel Collector sidecar. Explore it in a Kibana dashboard— see the
[Observability](observability.md) page for the panels to expect.

---

**Next:** read [Architecture](architecture.md) for how the pieces fit together, or
[CI Versions](ci-versions.md) for the GitLab vs GitHub details.
