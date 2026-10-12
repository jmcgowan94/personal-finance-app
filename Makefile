.PHONY: setup dev backend frontend migrate test seed-demo demo-csvs up down release-patch release-minor release-major

setup:            ## Install backend and frontend dependencies
	cd backend && uv sync
	cd frontend && npm install

migrate:          ## Create/upgrade the database schema
	cd backend && uv run alembic upgrade head

backend: migrate  ## Run the API on http://localhost:8000
	cd backend && uv run uvicorn app.main:app --reload --port 8000

frontend:         ## Run the web app on http://localhost:5173
	cd frontend && npm run dev

dev: migrate      ## Run API and web app together (Ctrl+C stops both)
	@trap 'kill 0' INT TERM; \
	(cd backend && uv run uvicorn app.main:app --reload --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

test:             ## Run backend tests and frontend type-check
	cd backend && uv run pytest
	cd frontend && npm run typecheck

seed-demo: migrate  ## Load 6 months of made-up demo data
	cd backend && uv run python -m app.scripts.seed_demo

demo-csvs:        ## Write demo CSVs to data/demo-statements to try the upload flow
	cd backend && uv run python -m app.scripts.seed_demo --out ../data/demo-statements

up:               ## Run everything in Docker (Postgres instead of SQLite)
	docker compose up --build

down:
	docker compose down

release-patch:    ## Release a bug-fix version (x.y.Z), tag and push
	scripts/release.sh patch

release-minor:    ## Release a feature version (x.Y.0), tag and push
	scripts/release.sh minor

release-major:    ## Release a breaking version (X.0.0), tag and push
	scripts/release.sh major
