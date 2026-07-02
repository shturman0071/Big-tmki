.PHONY: help test schemas docker-up docker-llm reindex demo finalize

RUNTIME := runtime
PY := python

help:
	@echo "TMKI targets:"
	@echo "  make test        - pytest runtime"
	@echo "  make schemas     - validate schemas/*.json"
	@echo "  make docker-up   - postgres+pgvector"
	@echo "  make docker-llm  - postgres + ollama profile"
	@echo "  make reindex     - resume re-index СКРУ-2"
	@echo "  make demo        - demo UI :8767"
	@echo "  make finalize    - finalize after 100% re-index"

test:
	cd $(RUNTIME) && $(PY) -m pytest -q

schemas:
	cd $(RUNTIME) && $(PY) -m pytest tests/test_schemas.py -q

docker-up:
	docker compose up -d postgres

docker-llm:
	docker compose --profile llm up -d

reindex:
	cd $(RUNTIME) && powershell -NoProfile -ExecutionPolicy Bypass -File scripts/rebuild_regulations_index.ps1 -Resume

demo:
	cd $(RUNTIME) && powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_tmki_demo_ui.ps1

finalize:
	cd $(RUNTIME) && powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_finalize.ps1
