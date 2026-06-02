# Benchmarking Suite

## Overview
This benchmark suite compares the monolith and microservices versions of WebIntel using Locust. It produces CSV and HTML reports, then generates a comparison chart.

## Prerequisites
- The monolith app must be running on `http://localhost:8000` for the monolith benchmark.
- The microservices gateway must be running on `http://localhost:8000` for the microservices benchmark.
- Python 3.12+ installed.
- `npm` is not required for benchmarks.

## Install
From the `benchmarks` directory:

```bash
pip install -r requirements.txt
```

## Run the full benchmark

```bash
bash run_benchmark.sh
```

This will create a timestamped results directory under `benchmarks/results/` and generate:
- `monolith_stats.csv`
- `monolith_report.html`
- `microservices_stats.csv`
- `microservices_report.html`
- `comparison_chart.png`

## Run Locust manually

Run the monolith UI:

```bash
locust -f locustfile_monolith.py
```

Open `http://localhost:8089` in your browser.

Run the microservices UI:

```bash
locust -f locustfile_microservices.py
```

## Metrics and meaning

| Metric | What it measures | Why it matters |
|---|---|---|
| Request Count | Total requests executed | Indicates overall workload |
| Failure Count | Total failed requests | Shows stability under load |
| Median Response Time | Middle response latency | Reflects typical user experience |
| Average Response Time | Mean latency | Reflects overall performance |
| Requests/s | Throughput | Compares service capacity |
| Failures/s | Failure rate | Indicates reliability |
| Comparison chart | Baseline vs distributed architecture | Helps evaluate microservice overhead |

## Notes
- The benchmark uses the gateway entry point for the microservices version.
- The analysis script reads Locust CSV statistics and renders a comparison chart.
