CONDA ?= conda
CONDA_ENV ?= mediaopt
PYTHON_VERSION ?= 3.10
CONDA_RUN = $(CONDA) run -n $(CONDA_ENV)

.PHONY: env install lint test api

env:
	$(CONDA) env list | awk '{print $$1}' | grep -qx "$(CONDA_ENV)" || $(CONDA) create -y -n $(CONDA_ENV) python=$(PYTHON_VERSION) pip

install: env
	$(CONDA_RUN) pip install -U pip
	$(CONDA_RUN) pip install -e .[dev]

lint:
	$(CONDA_RUN) ruff check src tests

test:
	$(CONDA_RUN) pytest -q

api:
	$(CONDA_RUN) uvicorn mediaopt.api.main:app --reload
