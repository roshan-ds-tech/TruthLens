# TruthLens · make setup | run | test | validate | demo
PY      ?= backend/.venv/bin/python
PYTHON3 ?= python3.11
export DYLD_FALLBACK_LIBRARY_PATH ?= /opt/homebrew/lib
export HF_HUB_OFFLINE = 1
export TRANSFORMERS_OFFLINE = 1

.PHONY: setup run dev test validate demo fixtures clean-data

setup:                ## Python venv + pinned deps + models (online once), UI deps + build
	test -d backend/.venv || $(PYTHON3) -m venv backend/.venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r backend/requirements.txt
	HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 $(PY) backend/scripts/fetch_models.py
	npm ci
	npm run build

run:                  ## API + built UI on http://localhost:8000 (fully offline)
	test -d dist || npm run build
	cd backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

dev:                  ## API with reload on :8000 and Vite UI on :5173
	(cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000 --reload) & npm run dev

test:                 ## all backend tests
	cd backend && .venv/bin/python -m pytest -q

validate:             ## seeded test set → validation/results/metrics.json + calibration.json
	$(PY) validation/run_validation.py

demo:                 ## build the demo case, analyze it, compare with samples/expected_report.json
	test -f samples/demo_case/clip.mp4 || $(PY) samples/make_demo.py
	$(PY) samples/check_demo.py

fixtures:             ## regenerate the small test fixtures
	$(PY) backend/tests/make_fixtures.py

clean-data:           ## delete local cases, evidence and reports (data/)
	rm -rf data
