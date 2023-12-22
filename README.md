# log8415-project

## Setup

**Prerequisites:**

- [Python 3.12](https://www.python.org) and [Poetry](https://python-poetry.org/)
- AWS credentials configured in `~/.aws/credentials`
- Learner Lab's private SSH key copied to `labsuser.pem` at the project root (+ `chmod 600`)

```sh
# Create the venv
poetry install

# Copy and edit secrets
cp src/common/secrets.example.py src/common/secrets.py
$EDITOR src/common/secrets.py
```

## Deploy

```sh
# Deploy one of the three architectures
poetry run python3 -m standalone
poetry run python3 -m cluster
poetry run python3 -m patterns
```

## Benchmark

**Prerequisites:**

- _standalone_ or _cluster_ deployment
- [sysbench](https://github.com/akopytov/sysbench)

```sh
./tools/benchmark.sh <mysql_host> <mysql_user> <mysql_password> <mysql_db>
```

## Cleanup

Terminate all project AWS resources.

```sh
poetry run tools/cleanup.py
```
