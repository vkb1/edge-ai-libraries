---
name: time-series-analytics-user
description: >
  Build a new time-series analytics use case on top of the deployed Time
  Series Analytics microservice — bring it up with Docker Compose (from a
  repo clone, or by fetching the compose files from GitHub when no clone
  exists) using the prebuilt intel/ia-time-series-analytics-microservice
  image, then author a UDF (Python) + TICKscript pair for the use case
  (threshold alerting, rate-of-change/spike detection, rolling-window
  anomaly detection, or pretrained-model inference), package it as a tar,
  deploy it via the REST API, and feed it data. Use when the user describes
  a sensor/metric monitoring or anomaly-detection scenario, wants to plug
  their own analytics logic or a trained scikit-learn model into a
  streaming pipeline, or asks to wire up MQTT/OPC UA alerting on top of
  this service. Not for modifying the microservice's own source code —
  that is time-series-analytics-dev.
---

# Time Series Analytics — User

Build new use cases on the deployed service: you write a small UDF and a
TICKscript, package them, deploy them over REST, and feed data in. **Run
commands yourself** and relay output. The service listens on host port
**5000**; Swagger UI is at `http://localhost:5000/docs`.

## When to Use

- Turn a monitoring/anomaly-detection description into a working UDF +
  TICKscript pair and deploy it
- Plug a pretrained scikit-learn model into the streaming pipeline
- Wire up MQTT (native TICKscript alert node) or OPC UA (REST endpoint)
  alerting on flagged points
- Debug why a deployed UDF isn't receiving data or a package upload fails

## Example Prompts

Sample problem-solving scenarios this skill handles end-to-end:

| Example | Problem it solves |
|---|---|
| [pressure-threshold-alert.md](./example-prompts/pressure-threshold-alert.md) | Flag sensor readings outside a safe range |
| [vibration-spike-mqtt-alert.md](./example-prompts/vibration-spike-mqtt-alert.md) | Flag sudden jumps between readings, alert over MQTT |
| [windturbine-anomaly-model.md](./example-prompts/windturbine-anomaly-model.md) | Run a pretrained anomaly-detection model per point |

## Reference Lookup

| File | Load when… |
|---|---|
| [`references/patterns.md`](./references/patterns.md) | choosing an approach — threshold, rate-of-change, rolling z-score, or pretrained model — **start here** for any new UDF |
| [`references/udf-authoring.md`](./references/udf-authoring.md) | writing the UDF's `Handler` methods, reading point fields, loading a model |
| [`references/tickscript-basics.md`](./references/tickscript-basics.md) | writing the tick script, wiring MQTT alerting |
| [`references/api-workflow.md`](./references/api-workflow.md) | the package's internal structure and a troubleshooting table for a failed upload or a silent pipeline (links out to the microservice's own docs for the deploy sequence and API reference) |

## 1. Get the service running

```bash
[ -f docker/docker-compose.yml ] && echo REPO || echo STANDALONE
```

- **REPO** (repo clone present) → `cd docker && docker compose up -d`
- **STANDALONE** (no clone) → fetch the compose files, then pull the
  published image explicitly so Compose runs it as-is instead of trying to
  build from a source tree that isn't there:
  ```bash
  RAW=https://raw.githubusercontent.com/open-edge-platform/edge-ai-libraries/main/microservices/time-series-analytics
  mkdir -p ts-analytics/docker && cd ts-analytics
  curl -fsSL $RAW/docker/docker-compose.yml -o docker/docker-compose.yml
  curl -fsSL $RAW/docker/.env -o docker/.env
  cd docker
  docker compose pull   # fetches intel/ia-time-series-analytics-microservice
  docker compose up -d  # image now exists locally, so this won't try to build
  ```
  If `docker compose pull` can't find the tag, check available tags for
  `intel/ia-time-series-analytics-microservice` on Docker Hub and set
  `IMAGE_SUFFIX` in `.env` accordingly.
- Already running (`curl -sf http://localhost:5000/health`) → skip to step 2.
- **Host has no Intel iGPU?** The compose file unconditionally mounts
  `/dev/dri` and adds it under `devices:`. If `docker compose up` fails on
  that device mount, comment out both the `devices:` entry and the
  `/dev/dri` line under `volumes:` in `docker/docker-compose.yml` — nothing
  else in this workflow needs a GPU unless you specifically set
  `udfs.device: GPU` in a UDF's config.

Wait for health before touching anything else:
```bash
until curl -sf http://localhost:5000/health; do sleep 5; done
```

## 2. Pick a pattern

Read [`references/patterns.md`](./references/patterns.md) and match the
user's description to a row in its table (threshold, rate-of-change,
rolling z-score, or pretrained model). Confirm the specific parameters
(field name, thresholds, window size, model file) before writing code.

## 3. Write the UDF and tick script

Copy the two templates and fill in the pattern-specific `point()` body from
`references/patterns.md`:

```bash
mkdir -p udfs tick_scripts   # standalone: these won't exist yet
cp .github/skills/time-series-analytics-user/assets/udf_stream_template.py udfs/<name>.py
cp .github/skills/time-series-analytics-user/assets/tick_template.tick tick_scripts/<name>.tick
```

(Standalone/no-clone: fetch these two template files from GitHub raw the
same way as the compose files above, under
`.github/skills/time-series-analytics-user/assets/`.)

Full method contract and gotchas: [`references/udf-authoring.md`](./references/udf-authoring.md).
Tick script details: [`references/tickscript-basics.md`](./references/tickscript-basics.md).

## 4. Package and deploy

```bash
.github/skills/time-series-analytics-user/scripts/package_udf.sh <name> .
curl -X POST http://localhost:5000/udfs/package -F "file=@<name>.tar"
curl -s -X POST http://localhost:5000/config -H 'Content-Type: application/json' \
  -d '{"udfs": {"name": "<name>"}}'
```

`package_udf.sh` validates file naming locally before tarring — read its
warnings if it fails. Full deploy sequence, config shape, and a
troubleshooting table for failed uploads or silent pipelines:
[`references/api-workflow.md`](./references/api-workflow.md).

## 5. Feed data and verify

```bash
curl -s -X POST http://localhost:5000/input -H 'Content-Type: application/json' \
  -d '{"topic": "point_data", "fields": {"value": 42.5}}'
docker logs -f ia-time-series-analytics-microservice
```

`topic` must equal the `.measurement(...)` value in the tick script.
Anomalies your UDF flags (via `write_response`) show up in this log; for
Kapacitor-internal errors, `docker exec -it
ia-time-series-analytics-microservice bash` then `cat
/tmp/log/kapacitor/kapacitor.log | grep -i error`.

## 6. Optional: alerting

- **MQTT** — set `config.json`'s `alerts.mqtt`, chain
  `|alert()...mqtt('<broker_name>')` in the tick script. Native, automatic.
- **OPC UA** — set `config.json`'s `alerts.opcua`, then explicitly call
  `POST /opcua_alerts` (not automatic — see
  [`tickscript-basics.md`](./references/tickscript-basics.md#alerting-two-different-mechanisms-dont-conflate-them)
  for why).

## Stop / clean

```bash
docker compose down -v   # from docker/
```
