# Settings (override at the CLI or in CI)
SHELL := /usr/bin/env
.ONESHELL:
.SHELLFLAGS := bash -euo pipefail -c

# Virtual environment
VENV = .venv
VENV_BIN = ${VENV}/bin
PYTHON = ${VENV}/bin/python
PIP = ${VENV}/bin/pip
PIP_CONF = ~/.config/pip/pip.conf
RUFF = ${VENV}/bin/ruff

SCRIPT ?=

define _defined
	test -n "${1}" || { echo ">>> ERROR: SCRIPT is a required argument (e.g. SCRIPT=examples/demo.py)"; exit 127; }
endef

define _exists
	test -f "$$(command -v ${1})" || { echo ">>> ERROR: ${1} not found in PATH"; exit 127; }
endef

# Will accumulate entries as "target::description|target2::description2|..."
HELP_ENTRIES :=

.PHONY: help venv init shell run run-script run-clean fmtcheck fmt lintcheck lint test build dev-install install-build clean

help: ## Show help
	@{ \
	awk 'BEGIN {FS=":.*##"; print "Targets:"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  \033[36m%-20s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST); \
	# Also print generated targets captured in HELP_ENTRIES
	# gsub function removes whitespace that would otherwise throw off padding in output
	printf '%s' '$(HELP_ENTRIES)' \
	  | awk -v RS='\\|' -F'::' 'NF>=2 {gsub(/^[[:space:]]+|[[:space:]]+$$/,"",$$1); printf "  \033[36m%-21s\033[0m %s\n", $$1, $$2 }'; \
	}

venv: ## Create python virtual environment and install development dependencies
	@echo ">>> Creating python virtual environment ..."
	python3 -m venv ${VENV}
	cp ${PIP_CONF} ${VENV}
	${PIP} install -r requirements.txt -r requirements-dev.txt -r requirements-test.txt

init: venv dev-install ## Create python virtual environment, install development dependencies, and install package

shell: ${VENV} ## Drop into python shell in virtual environment
	@echo ">>> Dropping into shell with python virtual environment activated..."
	echo ">>> Type 'deactivate' or 'exit' to leave"
	bash --rcfile <(echo "source ${VENV}/bin/activate")

run: ${PYTHON} ## Run Python REPL
	@echo ">>> Starting Python REPL..."
	${PYTHON}

run-script: ${PYTHON} ## Run script specified by SCRIPT=
	@$(call _defined,${SCRIPT})
	$(call _exists,${SCRIPT})
	${PYTHON} ${SCRIPT}

run-clean: ${PYTHON} clean init ## Clean environment and run script specified by SCRIPT=
	@$(call _defined,${SCRIPT})
	$(call _exists,${SCRIPT})
	${PYTHON} ${SCRIPT}

fmtcheck: ${RUFF} ## Verify formatting
	@${RUFF} format --check -q || { echo "Run 'make fmt'"; exit 2; }

fmt: ${RUFF} ## Format with ruff
	@${RUFF} format

lintcheck: ${RUFF} ## Verify linting
	@${RUFF} check --no-fix -q || { echo "Run 'make lint'"; exit 2; }

lint: ${RUFF} ## Lint with ruff
	@${RUFF} check --fix

test: ## Test with pytest
	@${VENV}/bin/pytest

build: ${PYTHON} ## Build wheel & bdist
	@${PYTHON} -m build

dev-install: ${PIP} ## Install source in editable/development mode
	@${PIP} install -e .

install-build: ${PIP} ## Install built wheel file
	@${PIP} install dist/*.whl

clean: ## Remove virtual environment, caches, and artifacts
	@echo ">>> Cleaning up virtual environment, caches, and build artifacts..."
	rm -rf ${VENV} build/ dist/	.pytest_cache
	find . -type d \( -name __pycache__ -o -name *.egg-info \) -exec rm -rf {} +
	echo ">>> All clean!"