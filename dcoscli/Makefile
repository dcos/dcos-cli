PYTHON ?= python

check:
	$(PYTHON) -c "import sys; assert sys.version_info[:2] == (3,6)"
.PHONY: check

deps: check
	pip install -e .[dev]
.PHONY: deps

lint: check
	flake8 --verbose dcos_cli/ tests/
	pylint --disable=missing-docstring dcos_cli/ tests/
	pydocstyle --ignore=D104,D203 dcos_cli/
.PHONY: lint

test: lint
	pytest --cov=dcos_cli --cov-fail-under=100  --cov-report term-missing tests/
.PHONY: test

build:
	pyinstaller dcos.spec
.PHONY: build
