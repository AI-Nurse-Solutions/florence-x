PKGS := packages/florence-core packages/florence-edena packages/florence-connectors packages/florence-model-router packages/florence-cli
PYTHONPATH := packages/florence-core:packages/florence-edena:packages/florence-connectors:packages/florence-model-router:packages/florence-cli:apps/api
# A repo-local OPA binary (see `make opa-install`) is prepended to PATH in the
# test/policy recipes so the OPA parity leg of tests/policy/ runs instead of
# skipping. Set inline per-recipe for portability across make versions.
TOOLING_BIN := $(CURDIR)/.tooling/bin

.PHONY: install dev test lint demo up down policy-test opa-install
install:
	pip install -e packages/florence-core -e packages/florence-edena -e packages/florence-cli
	pip install ".[api,dev]"

opa-install:  ## Download a repo-local OPA binary into .tooling/bin (gitignored)
	@mkdir -p $(TOOLING_BIN)
	@OS=$$(uname -s | tr '[:upper:]' '[:lower:]'); \
	 ARCH=$$(uname -m); \
	 case "$$ARCH" in arm64|aarch64) A=arm64;; x86_64|amd64) A=amd64;; *) echo "unsupported arch $$ARCH"; exit 1;; esac; \
	 URL="https://openpolicyagent.org/downloads/latest/opa_$${OS}_$${A}_static"; \
	 echo "Downloading $$URL"; \
	 curl -fsSL "$$URL" -o $(TOOLING_BIN)/opa && chmod +x $(TOOLING_BIN)/opa; \
	 $(TOOLING_BIN)/opa version

demo:  ## Run the ICU handoff demo end-to-end (no services required)
	PYTHONPATH=$(PYTHONPATH) python -m florence_cli run examples/icu_handoff/workflow.yaml \
		--agent examples/icu_handoff/agent.yaml --reviewer auto

test:
	PATH="$(TOOLING_BIN):$$PATH" PYTHONPATH=$(PYTHONPATH) pytest -q

lint:
	ruff check .

up:
	docker compose -f docker/docker-compose.yml up --build

down:
	docker compose -f docker/docker-compose.yml down -v

policy-test:  ## Run the Rego decision-ladder tests (needs opa; `make opa-install`)
	PATH="$(TOOLING_BIN):$$PATH" opa test policies -v
