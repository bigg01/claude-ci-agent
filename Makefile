# Makefile — documentation (Zensical) and container image (Podman) workflows.
#
# Python tooling runs through uv. The container engine defaults to podman per
# CLAUDE.MD ("Do NOT use Docker"); override with CONTAINER_ENGINE=docker if needed.

CONTAINER_ENGINE ?= podman
IMAGE            ?= app-test
CONTAINERFILE    ?= Containerfile
PORT             ?= 8000
COMPOSE          ?= podman-compose
STACK_NET        ?= claude-ci-agent-local_default
PROMPT           ?= Reply with exactly: E2E_OK

.DEFAULT_GOAL := help

.PHONY: help install docs serve docs-build docs-clean build run test test-e2e \
        compose-build stack-up stack-down stack-logs ci-local dashboard agent clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Sync Python deps (incl. Zensical) into the uv environment
	uv sync --dev

# ---------------------------------------------------------------------------
# Documentation (Zensical)
# ---------------------------------------------------------------------------

docs: docs-build ## Alias for docs-build

serve: install ## Live-preview the docs at http://localhost:$(PORT)
	uv run zensical serve

docs-build: install ## Build the static docs site into site/
	uv run zensical build --clean

docs-clean: ## Remove the built docs site
	rm -rf site

# ---------------------------------------------------------------------------
# Container image
# ---------------------------------------------------------------------------

build: ## Build the container image ($(IMAGE)) with $(CONTAINER_ENGINE)
	$(CONTAINER_ENGINE) build -t $(IMAGE) -f $(CONTAINERFILE) .

run: ## Run the built image as a detached service
	$(CONTAINER_ENGINE) run -d --name test-service $(IMAGE)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

test: install ## Run the pytest suite (unit tests + config validation)
	uv run pytest

test-e2e: ## Run the container end-to-end test locally (SKIP_BUILD=1 to reuse the image)
	IMAGE=$(IMAGE) CONTAINERFILE=$(CONTAINERFILE) CONTAINER_ENGINE=$(CONTAINER_ENGINE) tests/e2e.sh

ci-local: ## Run the local CI test: stack up + telemetry e2e into Elasticsearch
	COMPOSE="$(COMPOSE)" tests/ci-local.sh

# ---------------------------------------------------------------------------
# Local stack (Podman Compose): Elasticsearch + Kibana + OTel Collector
# ---------------------------------------------------------------------------

compose-build: ## Build the agent image via the compose file
	$(COMPOSE) build

stack-up: ## Start Elasticsearch + Kibana + OTel Collector
	$(COMPOSE) up -d elasticsearch kibana otel-collector
	@echo "Kibana → http://localhost:5601   Elasticsearch → http://localhost:9200"

stack-down: ## Stop the stack and remove volumes
	$(COMPOSE) down -v

stack-logs: ## Tail the stack logs
	$(COMPOSE) logs -f

dashboard: ## Import the Kibana dashboard + data views (after stack-up)
	local/kibana-setup.sh

agent: ## Run a one-shot agent on the stack network (PROMPT=… ANTHROPIC_API_KEY=…)
	$(CONTAINER_ENGINE) run --rm --network $(STACK_NET) \
	  -e ANTHROPIC_API_KEY \
	  -e CLAUDE_CODE_ENABLE_TELEMETRY=1 -e OTEL_LOG_TOOL_CONTENT=1 \
	  -e OTEL_METRICS_EXPORTER=otlp -e OTEL_LOGS_EXPORTER=otlp \
	  -e OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
	  -e OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318 \
	  -e OTEL_METRIC_EXPORT_INTERVAL=5000 -e CLAUDE_PERSONALITY=agent \
	  $(IMAGE) claude --dangerously-skip-permissions -p "$(PROMPT)"

clean: docs-clean ## Remove docs site and the container image
	-$(CONTAINER_ENGINE) rmi $(IMAGE) 2>/dev/null || true
	-$(CONTAINER_ENGINE) rmi $(IMAGE) 2>/dev/null || true
