#!/bin/bash
set -e
RESULTS_DIR="./results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"
echo "=== Benchmarking Monolith ==="
echo "Make sure the monolith is running on port 8000 before continuing."
read -p "Press enter when monolith is ready..."
locust -f locustfile_monolith.py \
  --headless \
  --users 10 \
  --spawn-rate 2 \
  --run-time 60s \
  --csv "$RESULTS_DIR/monolith" \
  --html "$RESULTS_DIR/monolith_report.html" \
  --host http://localhost:8000

echo ""
echo "=== Benchmarking Microservices ==="
echo "Make sure the microservices stack is running on port 8000 before continuing."
read -p "Press enter when microservices are ready..."
locust -f locustfile_microservices.py \
  --headless \
  --users 10 \
  --spawn-rate 2 \
  --run-time 60s \
  --csv "$RESULTS_DIR/microservices" \
  --html "$RESULTS_DIR/microservices_report.html" \
  --host http://localhost:8000

echo ""
echo "=== Analyzing Results ==="
python analyze_results.py "$RESULTS_DIR"
echo "Done. Results saved to $RESULTS_DIR"
