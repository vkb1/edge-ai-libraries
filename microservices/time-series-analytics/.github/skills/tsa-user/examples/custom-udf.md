<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Example: Custom UDF with a Model File

Deploy a custom Python UDF that uses a scikit-learn model for inference.

This example uses a hypothetical `windturbine_anomaly_detector` UDF that loads
a `.pkl` model and runs CPU-based inference.

---

## Prerequisites

- A trained model saved as `windturbine_anomaly_detector.pkl`
- A Python UDF script `windturbine_anomaly_detector.py`
- A Kapacitor TICKScript `windturbine_anomaly_detector.tick`

---

## 1. Package the UDF

Create the tarball at the root of the component directory.
**The tar must not have a wrapping top-level directory:**

```bash
cd edge-ai-libraries/microservices/time-series-analytics/

# Organize files
mkdir -p udfs/ tick_scripts/ models/
cp /path/to/windturbine_anomaly_detector.py udfs/
cp /path/to/windturbine_anomaly_detector.tick tick_scripts/
cp /path/to/windturbine_anomaly_detector.pkl models/

# Create archive (top-level entries: udfs/, tick_scripts/, models/)
tar cf windturbine_anomaly_detector.tar udfs/ tick_scripts/ models/
```

---

## 2. Upload the Package

```bash
curl -s -X POST http://localhost:5000/udfs/package \
  -F "file=@windturbine_anomaly_detector.tar"
```

Expected response:
```json
{
  "status": "success",
  "message": "UDF deployment package 'windturbine_anomaly_detector.tar' uploaded successfully."
}
```

---

## 3. Configure the Service

```bash
curl -s -X POST http://localhost:5000/config \
  -H 'Content-Type: application/json' \
  -d '{
    "udfs": {
      "name": "windturbine_anomaly_detector",
      "models": "windturbine_anomaly_detector.pkl",
      "device": "CPU"
    }
  }'
```

**To use GPU inferencing** (requires Intel GPU + scikit-learn-intelex):
```bash
curl -s -X POST http://localhost:5000/config \
  -H 'Content-Type: application/json' \
  -d '{
    "udfs": {
      "name": "windturbine_anomaly_detector",
      "models": "windturbine_anomaly_detector.pkl",
      "device": "GPU"
    }
  }'
```

---

## 4. Send Turbine Sensor Data

Send a data point with the fields your TICKScript expects:

```bash
curl -s -X POST http://localhost:5000/input \
  -H 'Content-Type: application/json' \
  -d '{
    "topic": "turbine_data",
    "tags": {
      "turbine_id": "T001",
      "location": "wind_farm_A"
    },
    "fields": {
      "rpm": 14.5,
      "vibration": 0.003,
      "power_output_kw": 1500
    }
  }'
```

---

## 5. Add MQTT Alerts (Optional)

Reconfigure to also publish anomaly alerts to an MQTT broker:

```bash
curl -s -X POST http://localhost:5000/config \
  -H 'Content-Type: application/json' \
  -d '{
    "udfs": {
      "name": "windturbine_anomaly_detector",
      "models": "windturbine_anomaly_detector.pkl",
      "device": "CPU"
    },
    "alerts": {
      "mqtt": {
        "mqtt_broker_host": "ia-mqtt-broker",
        "mqtt_broker_port": 1883,
        "name": "my_mqtt_broker"
      }
    }
  }'
```

---

## 6. Verify

```bash
docker logs -f ia-time-series-analytics-microservice
```

Anomalous readings trigger a log entry and an MQTT message to the configured topic.

---

## Tips

- The `name` field in `udfs` must exactly match the `.py` and `.tick` filenames (without extension).
- `requirements.txt` inside the `udfs/` folder is installed automatically on first activation.
- To update the UDF, re-upload the package and re-call `POST /config` — no container restart needed.
- To reset to the built-in UDF, re-upload the default package and change `name` back to `temperature_classifier`.
