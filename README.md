# log8415-project

```sh
# Setup the venv
poetry install

# Copy and edit secrets
cp ./src/common/secrets.example.py ./src/common/secrets.py
$EDITOR ./src/common/secrets.py

# Deploy one of the three architectures
poetry run python3 -m standalone
poetry run python3 -m cluster
poetry run python3 -m patterns

# Run the benchmark
./tools/benchmark.sh

# Cleanup the deployment
poetry run ./tools/cleanup.py
```
