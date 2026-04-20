<!--
SPDX-FileCopyrightText: (C) 2025 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Copilot Instructions — Time Series Analytics Microservice

## Scope

These instructions apply to `microservices/time-series-analytics/` and its sub-directories.

## Project Context

- **Time Series Analytics (TSA)** is a real-time data analytics microservice that processes time series data through custom Python User-Defined Functions (UDFs).
- **Architecture**: FastAPI REST API → Kapacitor (stream processing) → Python UDFs → InfluxDB (storage). Optional OPC UA alert routing.
- **Runtime**: Python 3.13 on Debian slim. Kapacitor 1.8.3 for stream processing.
- **Deployment targets**: Docker Compose and Kubernetes (Helm).
- **Companion app**: `edge-ai-suites` → `manufacturing-ai-suite/industrial-edge-insights-time-series` deploys this microservice with sample apps (wind-turbine-anomaly-detection, weld-defect-detection).

## Directory Layout

```
time-series-analytics/
├── src/                  # Python source (main.py, classifier_startup.py, opcua_alerts.py)
├── tests/                # Unit tests (pytest + pytest-cov + pytest-asyncio)
├── tests-functional/     # Docker-based integration tests
├── simulator/            # Temperature data simulator for demos
├── udfs/                 # Example UDFs (temperature_classifier.py)
├── tick_scripts/         # Kapacitor TICK stream processing scripts
├── docker/               # docker-compose.yml, run.sh entrypoint, .env, GPU drivers
├── helm/                 # Kubernetes Helm chart (Chart.yaml, values.yaml, templates/)
├── config/               # Kapacitor configs (production + devmode)
├── docs/                 # User documentation
├── scripts/              # Build/utility scripts (GPU driver install)
├── Dockerfile            # Multi-stage Docker build
├── requirements.txt      # Python dependencies (pinned versions)
├── config.json           # Default UDF configuration
└── schema.json           # JSON Schema for config validation
```

## Technology Stack

| Component          | Technology                                                     |
| ------------------ | -------------------------------------------------------------- |
| Language           | Python 3.13                                                    |
| REST API           | FastAPI 0.135.0 + Uvicorn 0.41.0                              |
| Stream Processing  | Kapacitor 1.8.3 (InfluxData)                                  |
| ML Acceleration    | scikit-learn 1.6.1 + scikit-learn-intelex 2025.11.0 (Intel)   |
| Time Series DB     | InfluxDB client 5.3.2                                         |
| OPC UA             | asyncua 1.1.8                                                 |
| Serialization      | protobuf 7.34.0                                               |
| GPU Support        | dpctl 0.21.1 (Intel GPU)                                      |
| Container Base     | python:3.13-slim (Debian)                                     |
| Orchestration      | Docker Compose, Helm (Kubernetes)                              |

## Coding Rules

### Python Source (`src/`)

- Use type hints on all function signatures and Pydantic models for API contracts.
- Use `async`/`await` for FastAPI handlers and OPC UA client calls.
- Use the `logging` module (never `print()`); respect `KAPACITOR_LOGGING_LEVEL`.
- Handle errors with `HTTPException` for API endpoints and `try/except` with logging elsewhere.
- Use `threading.Event` for synchronization between startup and main threads.
- Follow existing docstring style (reStructuredText or Google style).
- Preserve Apache-2.0 SPDX license headers on all files.

### UDFs (`udfs/`)

- UDFs are Python scripts processed by the Kapacitor UDF agent framework.
- Each UDF must implement the Kapacitor UDF handler interface (`Handler` class with `info`, `init`, `point`, `snapshot`, `restore`).
- Place companion TICK scripts in `tick_scripts/` with matching names.

### Tests (`tests/`)

- Framework: `pytest` with `pytest-cov` and `pytest-asyncio`.
- Run tests: `cd microservices/time-series-analytics && ./tests/run_tests.sh`
- Alternatively: `PYTHONPATH=./src python3 -m pytest --cov=src tests`
- Test files follow `test_*.py` naming; use descriptive test function names.
- Mock external services (Kapacitor, InfluxDB, OPC UA) in unit tests.
- Aim for coverage reported in HTML (`/tmp/htmlcov`).

### Functional Tests (`tests-functional/`)

- Run in Docker Compose and k3s (Kubernetes) environments.
- Test files: `test_docker.py` (Docker compose), `test_helm.py` (Helm deployment).
- Helper utilities in `rest_api_utils.py`.
- Use `pytest-html` for test reports.

### Docker / Dockerfile

- Multi-stage build: builder stage for Kapacitor UDF agents, runtime stage for final image.
- Non-root user: `timeseries_user` (UID 1999, GID 2999).
- Healthcheck: Kapacitor ping endpoint.
- Security: read-only root filesystem, dropped capabilities, SecComp, no privilege escalation.
- Build args: `KAPACITOR_VERSION`, `PYTHON_VERSION`, `INSTALL_DRIVER_VERSION`, `COPYLEFT_SOURCES`.

### Docker Compose (`docker/`)

- Service: `ia-time-series-analytics-microservice`.
- Ports: 5000 (REST API), 9092 (Kapacitor).
- Environment variables configured in `docker/.env`.
- GPU support: `/dev/dri` device mounting and render group IDs.

### Helm Chart (`helm/`)

- Chart version format: `2026.1.0-helm` (semantic versioning).
- Deploy to `apps` namespace by default.
- REST API NodePort: 30002 (external), 5000 (internal).
- All security contexts must remain: `readOnlyRootFilesystem`, `runAsNonRoot`, `drop: [ALL]`.

### Configuration

- `config.json`: Specifies which UDF to load (default: `temperature_classifier`).
- `schema.json`: JSON Schema that validates config updates via REST API.
- `config/kapacitor.conf` and `config/kapacitor_devmode.conf`: Kapacitor daemon configs.

## Key Environment Variables

| Variable                              | Purpose                               | Default       |
| ------------------------------------- | ------------------------------------- | ------------- |
| `KAPACITOR_LOGGING_LEVEL`             | Logging level                         | INFO          |
| `KAPACITOR_URL`                       | Kapacitor service URL                 | (internal)    |
| `INFLUXDB_DBNAME`                     | InfluxDB database name                | datain        |
| `REST_API_ROOT_PATH`                  | FastAPI root path                     | (empty)       |
| `UDF_MAX_FILE_SIZE_MB`                | Max UDF tar upload size               | 100           |
| `CORE_PINNING`                        | CPU core preference                   | (disabled)    |
| `OPCUA_SECURE_MODE`                   | Enable OPC UA TLS                     | false         |
| `MODEL_REGISTRY_URL`                  | Model registry endpoint               | (empty)       |

## REST API Endpoints

| Method | Path              | Description                            |
| ------ | ----------------- | -------------------------------------- |
| GET    | `/health`         | Kapacitor daemon health check          |
| POST   | `/input`          | Ingest time series data points         |
| GET    | `/config`         | Get current configuration              |
| POST   | `/config`         | Update configuration (with validation) |
| POST   | `/opcua_alerts`   | Send alerts to OPC UA server           |
| POST   | `/upload_tar_file`| Upload UDF deployment package          |

## CI/CD Workflows

This microservice has five CI workflows in `.github/workflows/`:

1. **`timeseries-build-pull-request.yml`**: Pre-merge pipeline (build → unit test → functional test → scans). Triggers on push to `main` and PRs affecting TSA paths.
2. **`timeseries-unit-test.yaml`**: Runs `tests/run_tests.sh`, uploads coverage artifacts.
3. **`timeseries-weekly-functional-tests.yaml`**: Weekly functional tests with Docker + k3s. Scheduled Fridays 14:00 UTC.
4. **`timeseries-scans.yaml`**: Security scans (CodeQL, Bandit, Trivy FS/image/Dockerfile, Pylint, ClamAV virus, Docker Bench Security).
5. **`timeseries-build-weekly-images.yaml`**: Weekly Docker image builds pushed to GHCR. Scheduled Tuesdays 14:00 UTC.

Cross-repo workflows in `edge-ai-suites`:
- `industrial-edge-insights-time-series-pull-request.yml`: Builds both TSA microservice and sample apps, deploys wind-turbine and weld-defect apps.
- `industrial-edge-insights-time-series-scans.yml`: Trivy, Bandit, ClamAV, Docker Bench, CodeQL, Pylint scans for the sample app layer.
- `industrial-edge-insights-time-series-tests.yml`: Daily functional tests for both time-series and multimodal apps.

## Compliance Requirements

- **License Header**: Every source file (`.py`, `.sh`, `.yaml`, `.yml`) must include an Apache-2.0 SPDX license header.
- **No Secrets**: Never commit passwords, tokens, API keys, or credentials. Use GitHub Secrets or environment variables.
- **Third-Party Dependencies**: When adding new dependencies, declare them in the PR with name, version, and license. Ensure compatibility with Apache-2.0.
- **Security Scans**: All code must pass CodeQL, Bandit (Python), Trivy (container/filesystem), Pylint, and ClamAV checks that run in CI.

## PR Guidelines

- Follow the PR template: description, dependency declaration, testing evidence, compliance checklist.
- Keep changes focused—do not mix unrelated refactors.
- Ensure existing unit tests and functional tests pass before submitting.
- Review CODEOWNERS for required reviewers (`@vkb1 @sathyendranv @pooja-intel @SudarshanaPanda @rashmihe`).

## Validation Before Finishing

1. Run unit tests: `cd microservices/time-series-analytics && ./tests/run_tests.sh`
2. Run pylint: `pylint src/*.py`
3. Verify Dockerfile builds: `cd docker && docker compose build`
4. For Helm changes, verify: `helm lint helm/`
5. Ensure all new files have Apache-2.0 SPDX headers.
6. Do not commit `.env` files with real credentials.
