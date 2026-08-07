<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# API Guide

Full request / response details for every TSA microservice endpoint.

**Base URL:** `http://localhost:5000` (Docker Compose) · `http://<node_ip>:30002` (Helm)  
**Interactive docs:** append `/docs` to the base URL.

---

## GET `/health`

Check whether the Kapacitor daemon is running.

**Response 200:**
```json
{"status": "healthy"}
```

If Kapacitor is not yet started, the request may hang or return `503`.

---

## GET `/config`

Retrieve the current configuration.

**Query parameter:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `restart` | boolean | `false` | Restart the UDF deployment before returning config |

**Response 200:** Returns the current `config.json` contents as JSON.

```bash
# Just read config
curl -s http://localhost:5000/config

# Read config and restart the UDF service
curl -s "http://localhost:5000/config?restart=true"
```

---

## POST `/config`

Update the active UDF and alert configuration.

**Request body** (`application/json`):

```json
{
  "udfs": {
    "name": "<udf_name>",         // required — matches the .py and .tick filename
    "models": "<model_file>",     // optional — filename in the models/ folder of the package
    "device": "CPU"               // optional — "CPU" (default) or "GPU"
  },
  "alerts": {                     // optional
    "mqtt": {
      "mqtt_broker_host": "ia-mqtt-broker",
      "mqtt_broker_port": 1883,
      "name": "my_mqtt_broker"
    },
    "opcua": {
      "opcua_server": "opc.tcp://ia-opcua-server:4840/freeopcua/server/",
      "namespace": 1,
      "node_id": 2004
    }
  }
}
```

**Constraints:**
- `udfs.name` is **mandatory**
- Request body must be ≤ 5 KB
- If `models` is specified, the model file must already be present in the uploaded UDF package
- If `device` is `GPU`, the UDF must be compatible with `scikit-learn-intelex`

**Status codes:**

| Code | Meaning |
|------|---------|
| 200 | Configuration updated successfully |
| 413 | Payload exceeds 5 KB |
| 422 | Invalid/missing fields, invalid device, or UDF package files missing |
| 500 | Failed to write configuration to file |

---

## POST `/input`

Send a single time-series data point for processing by the active UDF.

**Request body** (`application/json`):

```json
{
  "topic": "point_data",          // required — identifies the data stream
  "tags": {                       // optional — key-value metadata
    "location": "factory1",
    "device": "sensor_A"
  },
  "fields": {                     // required — the actual measurements
    "temperature": 23.5,
    "humidity": 60
  },
  "timestamp": 1718000000000000000  // optional — epoch nanoseconds; 0 or absent = now
}
```

**Status codes:**

| Code | Meaning |
|------|---------|
| 200 | Data forwarded to Kapacitor |
| 422 | Validation error (missing `topic` or `fields`) |
| 503 | Kapacitor daemon is not running |

---

## POST `/opcua_alerts`

Forward an alert message to the configured OPC UA server.

**Prerequisite:** `opcua` section must be present in the current configuration.

**Request body** (`application/json`):
```json
{
  "message": "High temperature alert at factory1"
}
```

**Status codes:**

| Code | Meaning |
|------|---------|
| 200 | Alert forwarded to OPC UA server |
| 400 | OPC UA not configured |
| 500 | Failed to initialize OPC UA client |

---

## POST `/udfs/package`

Upload a `.tar` archive containing a UDF deployment package.

**Request:** `multipart/form-data` with a single `file` field.

**Required archive structure** (no wrapping directory):
```
udfs/
    <udf_name>.py
    requirements.txt       (optional)
tick_scripts/
    <udf_name>.tick
models/                    (optional)
    <model_file>
```

**Allowed file extensions:** `.py`, `.tick`, `.txt`, `.cb`, `.pkl`, `.json`,
`.joblib`, `.xml`, `.bin`, `.onnx`, `.pt`, `.pth`

**Maximum archive size:** 100 MB

**Status codes:**

| Code | Meaning |
|------|---------|
| 200 | Package uploaded and extracted successfully |
| 400 | Not a `.tar`, corrupt archive, security scan failed (path traversal, symlinks, encrypted payload, tar-bomb), or required folders/files missing |
| 413 | File exceeds 100 MB |
| 500 | Failed to extract on the server |
