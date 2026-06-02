SHELL := /bin/bash

.PHONY: monolith-up monolith-down micro-up micro-down test-monolith test-micro test-all benchmark clean help
help:
	@echo "WebIntel Thesis Project"
	@echo ""
	@echo "Monolith:"
	@echo "  make monolith-up      Build and start the monolith (http://localhost:8000)"
	@echo "  make monolith-down    Stop the monolith"
	@echo ""
	@echo "Microservices:"
	@echo "  make micro-up         Build and start all microservices"
	@echo "  make micro-down       Stop all microservices"
	@echo ""
	@echo "Endpoints (microservices):"
	@echo "  Dashboard:   http://localhost:3000"
	@echo "  Gateway API: http://localhost:8000"
	@echo "  Grafana:     http://localhost:3001"
	@echo "  Prometheus:  http://localhost:9090"
	@echo ""
	@echo "Testing:"
	@echo "  make test-monolith    Run monolith tests"
	@echo "  make test-micro       Run all microservice tests"
	@echo "  make test-all         Run everything"
	@echo ""
	@echo "Benchmarking:"
	@echo "  make benchmark        Run Locust benchmark suite"
	@echo ""
	@echo "  make clean            Remove build artifacts"
monolith-up:
	cd monolith && docker compose up --build -d
	@echo "Monolith running at http://localhost:8000"
monolith-down:
	cd monolith && docker compose down
micro-up:
	cd microservices && docker compose up --build -d
	@echo "Dashboard:  http://localhost:3000"
	@echo "API:        http://localhost:8000"
	@echo "Grafana:    http://localhost:3001"
	@echo "Prometheus: http://localhost:9090"
micro-down:
	cd microservices && docker compose down
test-monolith:
	cd monolith && python -m pytest -v
test-micro:
	cd microservices/services/storage && python -m pytest -v
	cd microservices/services/crawler && python -m pytest -v
	cd microservices/services/extractor && python -m pytest -v
	cd microservices/services/nlp && python -m pytest -v
	cd microservices/services/scheduler && python -m pytest -v
	cd microservices/services/gateway && python -m pytest -v
test-all: test-monolith test-micro
benchmark:
	cd benchmarks && pip install -r requirements.txt -q && bash run_benchmark.sh
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned."

