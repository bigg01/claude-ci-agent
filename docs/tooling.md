---
icon: lucide/terminal
---

# Tooling & Commands

Because the environment is completely rootless, substitute standard system/Docker
workflows with the commands below.

## Containerization & builds

!!! warning "Do NOT use Docker"

    Always use Podman.

```bash
podman build -t app-test .                 # build image
podman run -d --name test-service <image>  # run local container service
podman logs <container-id>                 # inspect container logs
```

## Development & testing

```bash
npm ci                          # install deps (or: pip install -r requirements.txt)
npm test                        # execute tests (or local test runner binaries)
npm run lint                    # linting check
```

## Documentation (Zensical via uv)

```bash
uv run zensical serve           # preview at http://localhost:8000
uv run zensical build           # build static site into site/
```

## Coding standards

- **Explicit error paths**— write defensive returns; don't rely on unhandled runtime catching.
- **Dependency minimization**— no third-party helper libraries without an explicit human directive.
- **Atomic mutations**— commit locally with conventional messages (`feat:`, `fix:`).
