<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Troubleshooting

Common failure modes and fixes for the Time Series Analytics microservice.

---

## Service Won't Start

**Symptom:** `docker compose up -d` exits immediately or the container restarts in a loop.

**Diagnosis:**
```bash
docker logs -f ia-time-series-analytics-microservice
docker logs -f ia-time-series-analytics-microservice | grep -i error
```

**Common causes:**

| Symptom in logs | Fix |
|----------------|-----|
| `Permission denied` on `/tmp/` | Ensure the tmpfs volume is correctly configured in `docker-compose.yml` |
| `Kapacitor failed to start` | Check `KAPACITOR_PORT` env var is not in use by another process |
| `cannot connect to InfluxDB` | Standalone TSA deployment does not require InfluxDB — verify `KAPACITOR_INFLUXDB_0_URLS_0` is empty |

---

## Health Endpoint Returns Non-200

**Symptom:** `curl http://localhost:5000/health` returns an error or hangs.

**Diagnosis:**
```bash
# Check if Kapacitor is running inside the container
docker exec -it ia-time-series-analytics-microservice bash
$ curl http://localhost:9092/kapacitor/v1/ping
```

**Cause:** Kapacitor takes up to 30 seconds to initialize on first boot. Wait and retry.

If Kapacitor never becomes healthy:
```bash
docker exec -it ia-time-series-analytics-microservice bash
$ cat /tmp/log/kapacitor/kapacitor.log | grep -i error
```

---

## UDF Not Activating After `POST /config`

**Symptom:** `POST /config` returns 422 with `"UDF deployment package validation failed for <udf_name>."`.

**Causes:**

1. **UDF package not uploaded first** — always upload via `POST /udfs/package` before calling `POST /config`.
2. **Filename mismatch** — `udfs.name` in the config must exactly match the `.py` and `.tick` filenames in the package (case-sensitive, without extension).
3. **Model file missing** — if `udfs.models` is set, the named model file must be inside the `models/` folder of the uploaded tar.

**Fix:** Re-upload the package with the correct file layout, then resubmit the config.

---

## `POST /udfs/package` Returns 400

**Symptom:** Upload is rejected.

| Error message | Fix |
|--------------|-----|
| `"Tar archive must contain a 'udfs/' folder with at least one .py file."` | Rebuild the tar so `udfs/` is at the root (no wrapping directory) |
| `"Tar archive must contain a 'tick_scripts/' folder with at least one .tick file."` | Add a corresponding `.tick` file for your UDF |
| `"Path traversal attack detected"` | The tar contains paths with `..` — rebuild with safe paths |
| `"Symlink detected"` | Remove symlinks from the archive before packaging |

---

## Input Data Not Being Processed

**Symptom:** `POST /input` returns 200 but no output appears in logs.

**Possible causes:**

1. **UDF not configured** — the configuration was not applied after upload. Run `GET /config` to verify the active UDF name matches your script.
2. **Kapacitor task not created** — after a successful `POST /config`, Kapacitor creates an internal task. Check:
   ```bash
   docker exec -it ia-time-series-analytics-microservice bash
   $ kapacitor list tasks
   ```
3. **Data field name mismatch** — the TICKScript filters on specific field names. Ensure the `fields` in your `POST /input` payload match what the `.tick` script expects.
4. **Data within normal range** — the default temperature classifier only flags values < 20 or > 25. Send `"temperature": 30` to trigger an anomaly.

---

## MQTT Alerts Not Delivered

**Symptom:** Anomalies are detected (visible in logs) but no MQTT messages arrive.

**Checklist:**
1. MQTT broker is running: `docker ps | grep mqtt`
2. `mqtt_broker_host` in the config is reachable from inside the container:
   ```bash
   docker exec -it ia-time-series-analytics-microservice ping ia-mqtt-broker
   ```
3. `mqtt_broker_port` matches the broker's actual listener port (default `1883`).
4. MQTT broker is included in `no_proxy` / `NO_PROXY` env vars.

---

## OPC UA Alerts Returning 400

**Symptom:** `POST /opcua_alerts` returns `{"detail": "OPC UA alerts are not configured in the service"}`.

**Fix:** Add the `opcua` section to the config via `POST /config` and ensure the OPC UA server is running and reachable:
```bash
docker exec -it ia-time-series-analytics-microservice bash
$ curl opc.tcp://ia-opcua-server:4840/freeopcua/server/
```

---

## Container Logs Show Kapacitor Errors

```bash
docker exec -it ia-time-series-analytics-microservice bash
$ cat /tmp/log/kapacitor/kapacitor.log | grep -i error
```

Common Kapacitor errors:

| Log message | Meaning | Fix |
|-------------|---------|-----|
| `task not enabled` | UDF task was not created | Re-send `POST /config` |
| `UDF process exited` | The Python UDF script crashed | Check the UDF for runtime errors; add logging to the script |
| `failed to write point` | InfluxDB write failed | For standalone mode, ensure `KAPACITOR_INFLUXDB_0_URLS_0` is empty |
