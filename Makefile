.PHONY: install api web test migration

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

# Après une modification de apps/api/models/tables.py : make migration m="ajout colonne x"
migration:
	cd apps/api && .venv/bin/alembic revision --autogenerate -m "$(m)"
