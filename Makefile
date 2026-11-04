.PHONY: install api web test

install:
	python3 -m venv apps/api/.venv
	apps/api/.venv/bin/pip install -r apps/api/requirements.txt
	npm --prefix apps/web install

api:
	apps/api/.venv/bin/uvicorn main:app --reload --app-dir apps/api --port 8000

web:
	npm --prefix apps/web run dev

test:
	cd apps/api && .venv/bin/pytest -q
