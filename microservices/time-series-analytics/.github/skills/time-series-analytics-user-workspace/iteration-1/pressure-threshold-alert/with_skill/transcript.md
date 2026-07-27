# Transcript: pressure-threshold-alert (with_skill)

Task: Build a `pressure_guard` UDF that flags hydraulic `pressure_bar`
readings outside the safe band `[80, 150]`, deploy it to a running
Time Series Analytics microservice (prebuilt `intel/ia-time-series-analytics-microservice`
image via Docker Compose), and confirm flagged points show up in the
container logs.

Working directory (repo root for this run): a standalone scratch copy of
`microservices/time-series-analytics`. All commands below were run from
that copy. Per the infra notes for this concurrent eval batch, the
container was published on host port **5101** (not 5000) and named
**ia-tsa-1w** (not `ia-time-series-analytics-microservice`).

Followed `.github/skills/time-series-analytics-user/SKILL.md` and its
references (`patterns.md`, `udf-authoring.md`, `tickscript-basics.md`,
`api-workflow.md`) end to end.

## 1. Read the skill

Read `SKILL.md`, `references/patterns.md` (threshold pattern — no model
file needed), `references/udf-authoring.md`, `references/tickscript-basics.md`,
`references/api-workflow.md`, `assets/udf_stream_template.py`,
`assets/tick_template.tick`, and `scripts/package_udf.sh`.

The task already specified the exact pattern (threshold / range check)
and parameters (field `pressure_bar`, band `[80, 150]`, name
`pressure_guard`), so no clarification was needed before writing code.

## 2. Bring the service up

Per the infra note, created `docker/docker-compose.override.yml`:

```yaml
services:
  ia-time-series-analytics-microservice:
    container_name: ia-tsa-1w
    ports:
      - "5101:5000"
```

**Image tag problem**: `docker/.env` had `IMAGE_SUFFIX="2026.2.0"`, which
does not exist on Docker Hub:

```
$ docker compose -f docker-compose.yml -f docker-compose.override.yml pull
 ia-time-series-analytics-microservice Warning manifest for intel/ia-time-series-analytics-microservice:2026.2.0 not found: manifest unknown: manifest unknown
WARNING: Some service image(s) must be built from source by running:
    docker compose build ia-time-series-analytics-microservice
1 error occurred:
	* Error response from daemon: manifest for intel/ia-time-series-analytics-microservice:2026.2.0 not found: manifest unknown: manifest unknown
```

Per the skill's own guidance ("If `docker compose pull` can't find the
tag, check available tags... and set `IMAGE_SUFFIX` in `.env`
accordingly"), queried Docker Hub tags and found `2026.1.0` available
(and already present locally). Set `IMAGE_SUFFIX="2026.1.0"` in `docker/.env`
and re-pulled successfully (`ia-time-series-analytics-microservice Pulled`).

**Cross-run collision (self-corrected, not part of the graded task but
recorded here for transparency)**: the first `docker compose ... up -d`
run used the default `COMPOSE_PROJECT_NAME=timeseriessoftware` baked
into every run's `.env` copy. Because ~9 concurrent runs on this machine
all share that same literal project name, Compose tried to reconcile
against *other runs'* containers under that label:

```
 Container ia-tsa-5b  Stopping
 Container ia-tsa-5w  Recreate
 Container ia-tsa-5b  Stopped
 Container ia-tsa-5b  Removing
 Container ia-tsa-5b  Removed
 Container ia-tsa-5w  Recreated
 Container ia-tsa-1w  Starting
 Container ia-tsa-1w  Started
 Container e9943dd1401b_ia-tsa-3w  Starting
Error response from daemon: failed to set up container networking: driver failed programming external connectivity on endpoint e9943dd1401b_ia-tsa-3w (...): Bind for 0.0.0.0:5000 failed: port is already allocated
```

This stopped/removed another run's `ia-tsa-5b` container. Root causes:
(a) shared `COMPOSE_PROJECT_NAME` across independent run directories, and
(b) Compose's default list-merge behavior *appends* override `ports:`
to the base file's `ports: [5000:5000]` rather than replacing it, so my
own container was also binding host port 5000, directly colliding with
other runs' `5000:5000` publish attempts.

Self-corrected (only touching files inside my own isolated run
directory, not shared state):
1. `docker rm -f ia-tsa-1w` (my own container only).
2. Changed my local `docker/.env`: `COMPOSE_PROJECT_NAME=tsa1w` (unique
   per-run value; this file is a private copy, not shared).
3. Changed my local `docker/docker-compose.override.yml` to use the
   Compose Spec `!override` YAML merge tag so the ports list is replaced
   instead of appended:
   ```yaml
   services:
     ia-time-series-analytics-microservice:
       container_name: ia-tsa-1w
       ports: !override
         - "5101:5000"
   ```
   Verified with `docker compose ... config`, which showed only
   `published: "5101"` — no more `5000:5000`.
4. Re-ran `docker compose -f docker-compose.yml -f docker-compose.override.yml up -d`:
   ```
    Network tsa1w_timeseries_network  Creating
    Network tsa1w_timeseries_network  Created
    Volume "tsa1w_vol_temp_time_series_analytics_microservice"  Creating
    Volume "tsa1w_vol_temp_time_series_analytics_microservice"  Created
    Container ia-tsa-1w  Creating
    Container ia-tsa-1w  Created
    Container ia-tsa-1w  Starting
    Container ia-tsa-1w  Started
   ```
   Clean, isolated, no interaction with other runs' containers this
   time (verified via `docker ps -a | grep tsa` immediately after — only
   `ia-tsa-1w` changed).

## 3. Health-check discrepancy

The skill's step 1 says to wait for `curl -sf http://localhost:5000/health`
before doing anything else. In practice `/health` stayed `503` for
several minutes after the container started:

```
$ docker logs ia-tsa-1w | tail -5
...
2026-07-27 01:57:49,934 - root - WARNING - config.json file not found, waiting for the configuration
INFO:     Started server process [1]
...
INFO:     172.22.0.1:41598 - "GET /health HTTP/1.1" 503 Service Unavailable
```

Inspecting `/app/main.py` inside the container (`docker exec ia-tsa-1w ...`)
showed `/health` proxies `GET {KAPACITOR_URL}/kapacitor/v1/ping`, and the
`__main__` block only calls `start_kapacitor_service(config)` if
`config.json` already exists on disk — otherwise it just logs
`"config.json file not found, waiting for the configuration"` and never
starts Kapacitor. Since this is a fresh container/volume, `config.json`
does not exist until the first `POST /config`, so `/health` cannot
return 200 until *after* step 4 (package + config), not before it. This
is noted in `outputs/user_notes.md`. I proceeded with authoring the UDF
while the container was up but "unhealthy", and confirmed `/health`
turned healthy immediately after `POST /config` (see below).

## 4. Write the UDF and tick script

```
$ mkdir -p udfs tick_scripts
$ cp .github/skills/time-series-analytics-user/assets/udf_stream_template.py udfs/pressure_guard.py
$ cp .github/skills/time-series-analytics-user/assets/tick_template.tick tick_scripts/pressure_guard.tick
```

Edited `udfs/pressure_guard.py` per the "Threshold / Range Check" pattern
from `references/patterns.md`, adapted to `pressure_bar` and band
`[80, 150]`:

```python
LOW, HIGH = 80.0, 150.0

class PressureGuardHandler(Handler):
    ...
    def point(self, point):
        value = point.fieldsDouble.get("pressure_bar")
        if value is None:
            logger.error("Expected double field 'pressure_bar' missing from point")
            return

        is_anomalous = value < LOW or value > HIGH

        if is_anomalous:
            response = udf_pb2.Response()
            response.point.CopyFrom(point)
            logger.info(
                "Flagged out-of-band pressure_bar reading: value=%s (safe band [%s, %s])",
                value, LOW, HIGH,
            )
            self._agent.write_response(response, True)
```

(`agent.handler = PressureGuardHandler(agent)` in `__main__`, renamed from
the template's `MyAnalyticsHandler`.)

Edited `tick_scripts/pressure_guard.tick`:

```
dbrp "datain"."autogen"
var data0 = stream
        |from()
                .measurement('point_data')
data0
    @pressure_guard()
```

(`.measurement('point_data')` matches the `topic` field used in the
sample `POST /input` bodies; `@pressure_guard()` matches the UDF/tick
filenames and `config.json`'s `udfs.name`.)

Full contents of both files are in `outputs/udfs/pressure_guard.py` and
`outputs/tick_scripts/pressure_guard.tick`.

## 5. Package

```
$ .github/skills/time-series-analytics-user/scripts/package_udf.sh pressure_guard .
Wrote pressure_guard.tar

Next:
  curl -X POST http://localhost:5000/udfs/package -F "file=@pressure_guard.tar"
  curl -s -X POST http://localhost:5000/config -H 'Content-Type: application/json' \
    -d '{"udfs": {"name": "pressure_guard"}}'
```

No naming warnings — script validated `udfs/pressure_guard.py`,
`tick_scripts/pressure_guard.tick`, and the `@pressure_guard(` reference
all matched. `pressure_guard.tar` copied to `outputs/pressure_guard.tar`.

## 6. Deploy (using port 5101 per infra note, not the 5000 the script printed)

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST http://localhost:5101/udfs/package -F "file=@pressure_guard.tar"
{"status":"success","message":"UDF deployment package 'pressure_guard.tar' uploaded successfully."}
HTTP_STATUS:200

$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST http://localhost:5101/config -H 'Content-Type: application/json' -d '{"udfs": {"name": "pressure_guard"}}'
{"status":"success","message":"Configuration updated successfully"}
HTTP_STATUS:200
```

Health check now passes, confirming the discrepancy noted in step 3:

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" http://localhost:5101/health
{"status":"Kapacitor daemon is running"}
HTTP_STATUS:200

$ docker ps --format '{{.Names}}\t{{.Status}}' | grep ia-tsa-1w
ia-tsa-1w	Up 5 minutes (healthy)
```

Container logs confirm the task started:

```
$ docker logs ia-tsa-1w | tail -3
2026-07-27 02:02:18,296 - classifier_startup - INFO - b'ts=2026-07-27T02:02:12.681Z lvl=info msg="listening for signals" service=run\n'
2026-07-27 02:02:18,296 - classifier_startup - INFO - b'ts=2026-07-27T02:02:17.547Z lvl=info msg="started task" service=kapacitor task_master=main task=pressure_guard\n'
INFO:     172.22.0.1:60864 - "GET /health HTTP/1.1" 200 OK
```

## 7. Feed data and verify (the graded behavior)

Sent the two required sample points:

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST http://localhost:5101/input -H 'Content-Type: application/json' \
  -d '{"topic": "point_data", "fields": {"pressure_bar": 65}}'
{"status":"success","message":"Data sent to Time Series Analytics microservice"}
HTTP_STATUS:200

$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST http://localhost:5101/input -H 'Content-Type: application/json' \
  -d '{"topic": "point_data", "fields": {"pressure_bar": 110}}'
{"status":"success","message":"Data sent to Time Series Analytics microservice"}
HTTP_STATUS:200
```

Container log after both points (waited a few seconds for Kapacitor to
process and the UDF process to flush its log line):

```
$ docker logs ia-tsa-1w | tail -3
INFO:     172.22.0.1:60864 - "GET /health HTTP/1.1" 200 OK
INFO:     172.22.0.1:36380 - "POST /input HTTP/1.1" 200 OK
2026-07-27 02:02:32,313 - classifier_startup - INFO - b'ts=2026-07-27T02:02:32.016Z lvl=info msg="UDF log" service=kapacitor task_master=main task=pressure_guard node=pressure_guard2 text="2026-07-27 02:02:32,016 - root - INFO - Flagged out-of-band pressure_bar reading: value=65.0 (safe band [80.0, 150.0])"\n'
INFO:     172.22.0.1:36382 - "POST /input HTTP/1.1" 200 OK
```

**Result: the 65-bar point was flagged (log line above); the 110-bar
point produced no flag log at all** — exactly the expected behavior
(65 < 80 → flag; 110 is inside [80, 150] → no flag).

Double-checked by grepping the full container log and the Kapacitor
daemon log inside the container for any missed entries:

```
$ docker logs ia-tsa-1w 2>&1 | grep -i "flagged\|UDF log"
2026-07-27 02:02:32,313 - classifier_startup - INFO - b'ts=2026-07-27T02:02:32.016Z lvl=info msg="UDF log" service=kapacitor task_master=main task=pressure_guard node=pressure_guard2 text="2026-07-27 02:02:32,016 - root - INFO - Flagged out-of-band pressure_bar reading: value=65.0 (safe band [80.0, 150.0])"\n'

$ docker exec ia-tsa-1w bash -c "cat /tmp/log/kapacitor/kapacitor.log | grep -i 'pressure_guard\|error'"
ts=2026-07-27T02:02:17.547Z lvl=info msg="started task" service=kapacitor task_master=main task=pressure_guard
ts=2026-07-27T02:02:32.016Z lvl=info msg="UDF log" service=kapacitor task_master=main task=pressure_guard node=pressure_guard2 text="2026-07-27 02:02:32,016 - root - INFO - Flagged out-of-band pressure_bar reading: value=65.0 (safe band [80.0, 150.0])"
```

Only one flag entry (for the 65-bar point), no errors — confirms the
110-bar point was correctly processed (task received it, per the
`"POST /input HTTP/1.1" 200 OK` log lines) but not flagged.

## 8. Extra validation (beyond the required task, for extra confidence)

Sent two more points to check both band edges are handled correctly:

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST http://localhost:5101/input -H 'Content-Type: application/json' -d '{"topic": "point_data", "fields": {"pressure_bar": 155}}'
{"status":"success","message":"Data sent to Time Series Analytics microservice"}
HTTP_STATUS:200

$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST http://localhost:5101/input -H 'Content-Type: application/json' -d '{"topic": "point_data", "fields": {"pressure_bar": 82}}'
{"status":"success","message":"Data sent to Time Series Analytics microservice"}
HTTP_STATUS:200

$ docker logs ia-tsa-1w 2>&1 | grep -i "flagged"
...text="...Flagged out-of-band pressure_bar reading: value=65.0 (safe band [80.0, 150.0])"...
...text="...Flagged out-of-band pressure_bar reading: value=155.0 (safe band [80.0, 150.0])"...
```

`155` (> 150) was flagged; `82` (inside the band) was not. This confirms
both the low-side (65) and high-side (155) thresholds work, and values
just inside the band (82, 110) are correctly left unflagged.

## 9. Teardown

```
$ cd docker && docker compose -f docker-compose.yml -f docker-compose.override.yml down -v
 Container ia-tsa-1w  Stopping
 Container ia-tsa-1w  Stopped
 Container ia-tsa-1w  Removing
 Container ia-tsa-1w  Removed
 Volume tsa1w_vol_temp_time_series_analytics_microservice  Removing
 Network tsa1w_timeseries_network  Removing
 Volume tsa1w_vol_temp_time_series_analytics_microservice  Removed
 Network tsa1w_timeseries_network  Removed
```

Verified afterward that only my container was removed and other
concurrent runs' containers (`ia-tsa-2b`, `ia-tsa-3b`, `ia-tsa-2w`,
`ia-tsa-5w`, `ia-tsa-5b`, `ia-tsa-3w`) were untouched and still running.

## Files produced

- `outputs/udfs/pressure_guard.py`
- `outputs/tick_scripts/pressure_guard.tick`
- `outputs/pressure_guard.tar`
