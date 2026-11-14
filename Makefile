.PHONY: setup dev api web types test sample demo fixture audit

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

# make audit repo=. policy=docs/privacy.html [site=https://...] [fail_on=red|amber|never] [markdown=report.md]
# Paths are relative to the repo root; URLs are passed through unchanged.
from_root = $(if $(filter http://% https://%,$(1)),$(1),$(abspath $(1)))

audit:
	@test -n "$(policy)" || { echo "usage: make audit policy=PATH_OR_URL [repo=PATH_OR_URL] [site=URL] [fail_on=red|amber|never] [markdown=FILE]"; exit 2; }
	cd api && uv run python -m app.cli --policy "$(call from_root,$(policy))" \
		$(if $(repo),--repo "$(call from_root,$(repo))") $(if $(site),--site "$(site)") \
		$(if $(markdown),--markdown "$(abspath $(markdown))") --fail-on $(or $(fail_on),red)
