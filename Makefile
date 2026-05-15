.PHONY: install install-streamlit check test ingest recommend rank api streamlit

PYTHON := $(shell test -x .venv/bin/python && echo .venv/bin/python || command -v python3 || command -v python)

install:
	$(PYTHON) -m pip install -e ".[dev]"

install-streamlit:
	$(PYTHON) -m pip install -e ".[dev,streamlit]"

check:
	$(PYTHON) -m restaurant_recs check

test:
	$(PYTHON) -m pytest -q

ingest:
	$(PYTHON) -m restaurant_recs ingest $(if $(LIMIT),--limit $(LIMIT),)

recommend:
	$(PYTHON) -m restaurant_recs recommend $(ARGS)

rank:
	$(PYTHON) -m restaurant_recs rank $(ARGS)

api:
	$(PYTHON) -m uvicorn phase4.app:app --reload --host 127.0.0.1 --port 8000

streamlit:
	$(PYTHON) -m streamlit run streamlit_app/app.py --server.port 8501
