# log8415-project

```
# Setup the venv
poetry install

# Deploy one of the three architectures
poetry run python3 -m standalone
poetry run python3 -m cluster
poetry run python3 -m patterns

# Run the benchmark
./tools/benchmark.sh

# Cleanup the deployment
poetry run ./tools/cleanup.py
```
