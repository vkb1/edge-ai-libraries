<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Service Setup Reference

Full details for deploying the Time Series Analytics microservice.

---

## Prerequisites

- Docker Engine ≥ 24.0 and Docker Compose v2
- Non-root Docker access: [Manage Docker as a non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user)
- For GPU inferencing: Intel GPU drivers installed on the host

**System requirements:** [docs/user-guide/get-started/system-requirements.md](../../../../docs/user-guide/get-started/system-requirements.md)

---

## Clone the Repository

```bash
git clone https://github.com/open-edge-platform/edge-ai-libraries.git -b main
cd edge-ai-libraries/microservices/time-series-analytics
```

---

## Docker Compose Deployment

### Build the Image

```bash
cd docker/
docker compose build
```

To include copyleft licensed sources:
```bash
docker compose build --build-arg COPYLEFT_SOURCES=true
```

### Environment Variables (`.env`)

The `docker/.env` file contains tunable values. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKER_REGISTRY` | Registry prefix for the image | `""` |
| `TIME_SERIES_ANALYTICS_IMAGE` | Image name | `ia-time-series-analytics-microservice` |
| `IMAGE_SUFFIX` | Image tag | `latest` |
| `KAPACITOR_PORT` | Internal Kapacitor port | `9092` |
| `LOG_LEVEL` | Kapacitor logging level | `INFO` |
| `TIMESERIES_UID` | UID for the non-root user | (set in `.env`) |
| `TIMESERIES_USER_NAME` | Username for the non-root user | (set in `.env`) |

### Start the Service

```bash
docker compose up -d
```

**Service port:** `5000` (REST API + Swagger UI)

### Push Images (Optional)

Update `DOCKER_REGISTRY`, `DOCKER_USERNAME`, and `DOCKER_PASSWORD` in `.env`, then:
```bash
docker login $DOCKER_REGISTRY
docker compose push
```

---

## Helm Deployment (Kubernetes)

Detailed guide: [docs/user-guide/get-started/deploy-with-helm.md](../../../../docs/user-guide/get-started/deploy-with-helm.md)

```bash
cd edge-ai-libraries/microservices/time-series-analytics/helm/
helm install ia-time-series-analytics-microservice . --values values.yaml
```

**Service port (Helm):** `30002` (NodePort)  
**Swagger UI (Helm):** `http://<node_ip>:30002/docs`

---

## Proxy Configuration

If operating behind a corporate proxy, configure Docker:

```json
// ~/.docker/config.json
{
  "proxies": {
    "default": {
      "httpProxy": "http://<proxy_server>:<proxy_port>",
      "httpsProxy": "http://<proxy_server>:<proxy_port>",
      "noProxy": "127.0.0.1,localhost,ia-time-series-analytics-microservice,ia-influxdb,ia-mqtt-broker,ia-opcua-server"
    }
  }
}
```

---

## Log Rotation

Add to `/etc/docker/daemon.json` to prevent unbounded log growth:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5"
  }
}
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

---

## Stopping the Service

```bash
docker compose down -v   # -v removes named volumes (clears all state)
```
