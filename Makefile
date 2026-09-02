.PHONY: install lint format test run clean docker-build docker-run

install:
	python -m venv .venv
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install ruff black pytest pip-audit

lint:
	.venv/bin/ruff check src/ app.py tests/
	.venv/bin/ruff format --check src/ app.py tests/

format:
	.venv/bin/ruff check --fix src/ app.py tests/
	.venv/bin/ruff format src/ app.py tests/

test:
	.venv/bin/pytest tests/ -v

audit:
	.venv/bin/pip-audit -r requirements.txt

run:
	.venv/bin/python app.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov

docker-build:
	docker build -t docdiff:latest .

docker-run:
	docker run -p 29661:29661 --env-file .env docdiff:latest
