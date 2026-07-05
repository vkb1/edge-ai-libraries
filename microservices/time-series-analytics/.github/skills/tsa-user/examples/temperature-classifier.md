<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Example: Temperature Classifier (End-to-End)

Run the built-in temperature anomaly detection demo from start to finish.

The default UDF (`temperature_classifier`) flags any temperature reading that is
**< 20** or **> 25** degrees as an anomaly.

---

## 1. Clone and Build

```bash
git clone https://github.com/open-edge-platform/edge-ai-libraries.git -b main
cd edge-ai-libraries/microservices/time-series-analytics/docker
docker compose build
```

---

## 2. Start the Service

```bash
docker compose up -d
```

Wait for the service to become healthy:
```bash
curl -s http://localhost:5000/health
```

---

## 3. Upload the Built-in UDF Package

The default UDF is already inside the container. You still need to register it
via the upload endpoint so Kapacitor can find it:

```bash
cd edge-ai-libraries/microservices/time-series-analytics/
rm -f temperature_classifier.tar
tar cf temperature_classifier.tar udfs/ tick_scripts/

curl -s -X POST http://localhost:5000/udfs/package \
  -F "file=@temperature_classifier.tar"
```

Expected response:
```json
{"status": "success", "message": "UDF deployment package 'temperature_classifier.tar' uploaded successfully."}
```

---

## 4. Activate the UDF

```bash
curl -s -X POST http://localhost:5000/config \
  -H 'Content-Type: application/json' \
  -d '{"udfs": {"name": "temperature_classifier"}}'
```

Verify:
```bash
curl -s http://localhost:5000/config
```

---

## 5. Send a Normal Data Point (no anomaly)

```bash
curl -s -X POST http://localhost:5000/input \
  -H 'Content-Type: application/json' \
  -d '{
    "topic": "point_data",
    "fields": {"temperature": 22}
  }'
```

---

## 6. Send an Anomalous Data Point

```bash
curl -s -X POST http://localhost:5000/input \
  -H 'Content-Type: application/json' \
  -d '{
    "topic": "point_data",
    "tags": {"location": "factory1"},
    "fields": {"temperature": 30}
  }'
```

---

## 7. Verify Results

```bash
docker logs -f ia-time-series-analytics-microservice
```

You should see a log entry for the anomalous temperature value (30 > 25).

---

## 8. Run the Continuous Simulator

Instead of sending individual data points, run the built-in simulator to
generate a stream of temperature readings:

```bash
cd edge-ai-libraries/microservices/time-series-analytics/
python3 -m venv venv
source venv/bin/activate
pip3 install -r simulator/requirements.txt
python3 simulator/temperature_input.py --port 5000
```

Keep watching the container logs to see anomaly detections in real time:
```bash
docker logs -f ia-time-series-analytics-microservice
```

---

## 9. Stop the Service

```bash
cd edge-ai-libraries/microservices/time-series-analytics/docker
docker compose down -v
```
