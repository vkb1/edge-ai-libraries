---
name: tsa-user
description: >
  Deploy and operate the Time Series Analytics (TSA) microservice.
  Use this skill whenever a user wants to: deploy the service with Docker Compose
  or Helm; upload a UDF deployment package; configure the UDF and alert settings;
  send time-series data points for processing; check service health; or understand
  how to set up temperature anomaly detection or custom analytics. Also trigger on
  phrases like "run time series analytics", "upload UDF", "configure kapacitor",
  "send sensor data", "anomaly detection", "MQTT alerts", "OPC UA alerts",
  "set up TSA", or "ingest data".
argument-hint: >
  Describe what you want to do (e.g. "deploy the time series analytics service
  and run the temperature classifier UDF")
license: Apache-2.0
metadata:
  version: "1.0.0"
  tags: "tsa time-series analytics deployment udf kapacitor"
---

<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Time Series Analytics (TSA) User Skill

Deploy the TSA microservice and walk the user through uploading a UDF, configuring
analytics, and ingesting time-series data.

> **Always run commands yourself** and relay results; do not ask the user to run them.

## When to Use

- User wants to deploy the TSA microservice with Docker Compose or Helm
- User wants to upload a custom User-Defined Function (UDF) deployment package
- User wants to configure the active UDF, model, alerts (MQTT / OPC UA)
- User wants to send JSON data points or Telegraf line-protocol data for analysis
- User wants to check whether the Kapacitor daemon is healthy
- User is troubleshooting anomaly detection, alert delivery, or a stuck UDF

## API Endpoints at a Glance

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check Kapacitor daemon health |
| `/config` | GET | Retrieve current configuration |
| `/config` | POST | Update UDF / alert configuration |
| `/input` | POST | Send a JSON data point for processing |
| `/opcua_alerts` | POST | Forward an alert to the OPC UA server |
| `/udfs/package` | POST | Upload a `.tar` UDF deployment package |

**Default port:** `5000` (Docker Compose). Helm default: `30002`.  
**Swagger UI:** `http://localhost:5000/docs`

## Common Mistakes to Avoid

| Mistake | Correct |
|---------|---------|
| Using a wrong port | Always use port **`5000`** (Docker) or **`30002`** (Helm) |
| Sending a config without uploading the UDF first | Upload UDF package **before** calling `POST /config` |
| Calling `POST /config` with a missing `name` field | `udfs.name` is **mandatory** |
| Expecting OPC UA to work without `opcua` config | Add `opcua` section and have the server running |
| Exceeding the 5 KB config limit | Keep `config.json` ≤ 5 KB |
| Uploading a `.tar` with a wrapping top-level directory | Tar must have `udfs/` and `tick_scripts/` at the top level |

---

## Reference Lookup

Read a reference file only when you need its detail:

| Reference | When to read |
|-----------|-------------|
| [service-setup.md](./references/service-setup.md) | Cloning the repo, building and starting the service, env vars, Helm deployment |
| [api-guide.md](./references/api-guide.md) | Full endpoint details, request/response shapes, status codes |
| [troubleshooting.md](./references/troubleshooting.md) | Container issues, UDF not activating, Kapacitor errors, alert delivery failures |

## Example Scenarios

Read these only if the user's request matches:

| File | Covers |
|------|--------|
| [examples/temperature-classifier.md](./examples/temperature-classifier.md) | Full end-to-end: deploy → upload → configure → ingest → verify results |
| [examples/custom-udf.md](./examples/custom-udf.md) | Packaging and deploying a custom Python UDF with a model file |

---

## Procedure

### Execution Overview

```
Step 0 (gather requirements — interactive)
  │
  ├──► Step 1 (deploy service)
  └──► Step 2 (upload UDF package)
         │
         └──► Step 3 (configure UDF and alerts)
                │
                └──► Step 4 (ingest data and verify)
```

---

### Step 0 — Gather Requirements

Determine from the user's prompt:

| Required | What to look for | Default if absent |
|----------|-----------------|-------------------|
| **Deployment type** | "Docker", "Helm", "k8s" | Docker Compose |
| **UDF name** | Python script name without `.py` | `temperature_classifier` (built-in) |
| **Model file** | `.pkl`, `.onnx`, `.pt`, etc. | None (simple logic UDFs need no model) |
| **Device** | "CPU" or "GPU" | `CPU` |
| **Alerts** | "MQTT", "OPC UA", or none | None |
| **Data source** | "REST API", "simulator", "Telegraf" | REST API (`POST /input`) |

If the user just wants the default temperature anomaly demo, skip to Step 1 — no UDF upload needed.

---

### Step 1 — Deploy the Service

Read [service-setup.md](./references/service-setup.md) for full details.

**Quick start (Docker Compose, default demo):**
```bash
# Clone the repo if not already present
git clone https://github.com/open-edge-platform/edge-ai-libraries.git -b main
cd edge-ai-libraries/microservices/time-series-analytics/docker

# Build and start
docker compose build
docker compose up -d
```

Verify the service is healthy before proceeding:
```bash
curl -s http://localhost:5000/health
# Expected: {"status": "healthy"} or similar
```

If the container is not healthy, check logs:
```bash
docker logs -f ia-time-series-analytics-microservice
```

---

### Step 2 — Upload a UDF Deployment Package (skip for built-in UDFs)

The default `temperature_classifier` UDF is already built into the image.
Only follow this step when the user brings a **custom** UDF.

A valid `.tar` archive must have this layout (no wrapping top-level directory):
```
udfs/
    <udf_name>.py          (required)
    requirements.txt       (optional — extra pip packages)
tick_scripts/
    <udf_name>.tick        (required)
models/                    (optional)
    <model_files>
```

Create and upload the archive:
```bash
cd edge-ai-libraries/microservices/time-series-analytics/
# Package from the component root
tar cf <udf_name>.tar udfs/ tick_scripts/

# Upload (max 100 MB)
curl -s -X POST http://localhost:5000/udfs/package \
  -F "file=@<udf_name>.tar"
# Expected: {"status": "success", "message": "UDF deployment package '<udf_name>.tar' uploaded successfully."}
```

**Allowed file extensions in the tar:** `.py`, `.tick`, `.txt`, `.cb`, `.pkl`,
`.json`, `.joblib`, `.xml`, `.bin`, `.onnx`, `.pt`, `.pth`

---

### Step 3 — Configure the UDF and Alerts

After the UDF package is on the server, push `POST /config` to activate it.

Read [api-guide.md](./references/api-guide.md) for the full schema.

**Minimal configuration (no model, no alerts):**
```bash
curl -s -X POST http://localhost:5000/config \
  -H 'Content-Type: application/json' \
  -d '{"udfs": {"name": "<udf_name>"}}'
```

**With a model file and GPU device:**
```bash
curl -s -X POST http://localhost:5000/config \
  -H 'Content-Type: application/json' \
  -d '{
    "udfs": {
      "name": "<udf_name>",
      "models": "<model_file.pkl>",
      "device": "GPU"
    }
  }'
```

**With MQTT alerts:**
```bash
curl -s -X POST http://localhost:5000/config \
  -H 'Content-Type: application/json' \
  -d '{
    "udfs": {"name": "<udf_name>"},
    "alerts": {
      "mqtt": {
        "mqtt_broker_host": "ia-mqtt-broker",
        "mqtt_broker_port": 1883,
        "name": "my_mqtt_broker"
      }
    }
  }'
```

Verify the configuration was applied:
```bash
curl -s http://localhost:5000/config
```

---

### Step 4 — Ingest Data and Verify Results

**Send a single JSON data point:**
```bash
curl -s -X POST http://localhost:5000/input \
  -H 'Content-Type: application/json' \
  -d '{
    "topic": "point_data",
    "tags": {"location": "factory1", "device": "sensor_A"},
    "fields": {"temperature": 30.5},
    "timestamp": 0
  }'
# Expected: {"status": "success", ...}
```

`timestamp` is optional — if `0` or omitted, the current time is used.
`tags` is optional.

**Run the built-in temperature simulator** (generates continuous data):
```bash
cd edge-ai-libraries/microservices/time-series-analytics/
python3 -m venv venv
source venv/bin/activate
pip3 install -r simulator/requirements.txt
python3 simulator/temperature_input.py --port 5000
```

**Watch results in the container logs:**
```bash
docker logs -f ia-time-series-analytics-microservice
```

Anomalies (temperatures < 20 or > 25 for the default UDF) are logged as they are detected.

---

### Stopping the Service

```bash
cd edge-ai-libraries/microservices/time-series-analytics/docker
docker compose down -v
```

The `-v` flag removes named volumes (clears stored state). Omit it if you want
to retain the state across restarts.
