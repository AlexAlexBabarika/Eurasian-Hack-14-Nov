.PHONY: setup dev api web types test sample demo fixture

setup:
	cd api && uv sync && uv run playwright install chromium
	cd web && pnpm install

dev:
	$(MAKE) -j2 api web

api:
	cd api && ALLOW_LOCAL_INPUTS=$${ALLOW_LOCAL_INPUTS:-0} uv run uvicorn app.main:app --reload --port 8000

web:
	cd web && pnpm dev

types:
	cd api && uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > /tmp/groundtruth-openapi.json
	cd web && pnpm exec openapi-typescript /tmp/groundtruth-openapi.json -o src/lib/api-types.ts

test:
	cd api && uv run ruff check . && uv run pytest -q
	cd web && pnpm exec tsc --noEmit && pnpm lint

sample:
	cd api && uv run python -m app.sample

demo:
	DEMO_MODE=cached $(MAKE) dev

fixture:
	cd demo/fixture-app && python3 -m http.server 4100
