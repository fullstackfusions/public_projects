.PHONY: env doctor up up-lite up-metal down clean logs run bench compress-bench loghub-bench frontier-dry frontier chaos screenshots lint

# Create .env from the template only if it does not exist (never overwrites your keys).
env:
	@test -f .env && echo ".env exists; leaving it alone" || (cp .env.example .env && echo "created .env: add SCALEDOWN_API_KEY")

# Preflight: docker memory, keys, cached models, port conflicts.
doctor:
	@scripts/doctor.sh

# Full stack, CPU-only inference at 32k ctx (the configuration all published numbers use).
# Needs Docker Desktop memory >= 16 GB.
up:
	docker compose up -d --build

# Same stack for an 8 GB Docker Desktop: 16k ctx, one worker. Fine for trying it out.
up-lite:
	AGENT_NUM_CTX=16384 docker compose up -d --build --scale worker=1

# Dev only: native Ollama app on the Mac (Metal GPU) instead of the CPU container.
up-metal:
	docker compose -f docker-compose.yml -f compose.metal.yml up -d --build api prodsim worker

down:
	docker compose down

# End of testing: remove this project's containers, networks, data volumes (Postgres runs,
# Redis queue) and the image it built. Keeps results/ on the host, pulled images (postgres,
# redis, ollama) and Ollama models in ~/.ollama. Asks first; `make clean YES=1` skips the prompt.
clean:
	@if [ "$(YES)" != "1" ]; then \
	  echo "Deletes this project's Postgres runs, Redis queue and built image. results/ is kept."; \
	  read -p "Type 'yes' to continue: " ans && [ "$$ans" = yes ] || { echo "aborted"; exit 1; }; \
	fi
	docker compose --profile bench down --volumes --remove-orphans --rmi local

logs:
	docker compose logs -f worker

# Page the agent: make run SCENARIO=flaky-metrics-loop PROFILE=scaledown_fold
SCENARIO ?= db-pool-exhaustion
PROFILE ?= scaledown_fold
run:
	curl -s -X POST localhost:8000/api/runs -H 'content-type: application/json' \
	  -d '{"scenario":"$(SCENARIO)","profile":"$(PROFILE)"}' | python3 -m json.tool

# End-to-end matrix through the production path (slow on CPU: plan hours).
bench:
	docker compose --profile bench run --rm bench python -m oncall.bench.run_matrix

# Component benches: no agent, minutes not hours.
compress-bench:
	docker compose --profile bench run --rm --no-deps bench python -m oncall.bench.compress_bench

loghub-bench:
	docker compose --profile bench run --rm --no-deps bench python -m oncall.bench.loghub_bench --lines 2000

frontier-dry:
	docker compose --profile bench run --rm --no-deps bench python -m oncall.bench.frontier_bench

frontier:
	docker compose --profile bench run --rm --no-deps bench python -m oncall.bench.frontier_bench --execute

# Kill a worker mid-run; another reclaims the stream entry and resumes from the checkpoint.
# `make chaos RUN=<id>` kills the worker that owns that run (worker name = container id).
chaos:
	@if [ -n "$(RUN)" ]; then \
	  w=$$(curl -s localhost:8000/api/runs/$(RUN) | python3 -c "import sys,json;print(json.load(sys.stdin)['worker'])"); \
	  echo "killing worker $$w (owns run $(RUN))"; docker kill $$w; \
	else docker kill $$(docker compose ps -q worker | head -1); fi

screenshots:
	uv run --no-project --with playwright==1.55.0 python scripts/screenshots.py

lint:
	uvx ruff check src scripts
