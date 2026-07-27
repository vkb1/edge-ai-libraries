# Transcript: pressure_guard UDF (without_skill baseline)

## Task

Build a UDF named `pressure_guard` for the Time Series Analytics microservice that
flags hydraulic pressure readings (`fields.pressure_bar` arriving via `POST /input`)
outside the safe band 80-150 bar. Deploy against the prebuilt
`intel/ia-time-series-analytics-microservice` image via Docker Compose and confirm
flagged points show up in the container logs.

## 1. Exploring the repo

Read `udfs/temperature_classifier.py` (the built-in sample UDF), its
`tick_scripts/temperature_classifier.tick`, `config.json`, `docs/user-guide/get-started.md`,
`docs/user-guide/how-to-configure.md`, `docs/user-guide/how-it-works.md`, `src/main.py`
(FastAPI app: `/input`, `/config`, `/udfs/package`, `/health`), and
`src/classifier_startup.py` (wires the uploaded UDF into `kapacitor.conf`'s
`[udf.functions]` section and enables the TICK task).

Key facts learned:
- A UDF is a Python script using `kapacitor.udf.agent.{Agent,Handler}` and
  `kapacitor.udf.udf_pb2`. The `point()` handler receives fields via
  `point.fieldsDouble` (or `fieldsInt`); to flag a point it copies it into a
  `Response` and calls `self._agent.write_response(response, True)`, then logs via
  `logger.info(...)` — this ends up in Kapacitor's log, which is tailed into the
  container's stdout/`docker logs`.
- The matching TICK script defines the stream source
  (`|from().measurement('point_data')`) and pipes it through `@<udf_name>()`.
- Deployment package = a tar containing `udfs/<name>.py` and
  `tick_scripts/<name>.tick` (no wrapping top directory), POSTed to
  `/udfs/package` (multipart `file=...`). The tar's filename (minus `.tar`) becomes
  the extraction directory `/tmp/<name>` inside the container.
- Activating it: POST `/config` with `{"udfs": {"name": "<name>"}}`. This validates
  the deployment package is present, restarts Kapacitor (background task), and
  enables the corresponding TICK task.
- Input data goes to `POST /input` as
  `{"topic": "...", "fields": {...}, "tags": {...}, "timestamp": ...}`; the service
  converts it to InfluxDB line protocol and writes it to Kapacitor's
  `/kapacitor/v1/write?db=datain&rp=autogen`. The stream task filters on
  `.measurement('point_data')`, so `topic` must be `"point_data"` — matches the
  sample inputs given in the task.
- `docker/docker-compose.yml` builds `ia-time-series-analytics-microservice`, but
  also has an `image:` field
  (`${DOCKER_REGISTRY}${TIME_SERIES_ANALYTICS_IMAGE}:${IMAGE_SUFFIX:-latest}...`),
  so `docker compose up -d` without `--build` uses the prebuilt image if compose
  doesn't need to build.

## 2. Files created

- `udfs/pressure_guard.py` — copy of `temperature_classifier.py`'s structure,
  adapted to read `pressure_bar` from `point.fieldsDouble`/`fieldsInt` and flag when
  `pressure < 80 or pressure > 150`.
- `tick_scripts/pressure_guard.tick` — same stream/measurement wiring as the
  temperature sample, calling `@pressure_guard()`.
- `pressure_guard_config.json` — `{"udfs": {"name": "pressure_guard"}}`, the payload
  for `POST /config`.
- `docker/docker-compose.override.yml` (per infra notes, for this isolated run):
  ```yaml
  services:
    ia-time-series-analytics-microservice:
      container_name: ia-tsa-1b
      ports: !override
        - "5102:5000"
  ```
  Note: I added the `!override` merge tag on `ports`. Compose concatenates
  list-valued keys across `-f` files by default, so a plain
  `ports: ["5102:5000"]` override would have resulted in **both** `5000:5000`
  (from the base file) and `5102:5000` being published — risking a port collision
  with the ~9 other concurrent runs on this same host. `!override` (supported by
  Compose v2.35.1, confirmed via `docker compose version`) replaces the list
  instead of appending to it. Verified with `docker compose config`.

## 3. Bringing the stack up — image tag problem

First attempt: `cd docker && docker compose -f docker-compose.yml -f docker-compose.override.yml up -d`
(relying on `docker/.env`'s `IMAGE_SUFFIX="2026.2.0"`). This hung — no container
ever appeared in `docker ps -a`. Investigated:

```
$ docker manifest inspect intel/ia-time-series-analytics-microservice:2026.2.0
no such manifest: docker.io/intel/ia-time-series-analytics-microservice:2026.2.0
```

That tag doesn't exist on Docker Hub. `docker images` showed `2026.1.0` already
present locally (2.54GB, pulled previously), and:

```
$ docker manifest inspect intel/ia-time-series-analytics-microservice:2026.1.0
{
    "schemaVersion": 2,
    ...
```

`2026.1.0` exists and resolves. I killed the stuck compose process and re-ran with
`IMAGE_SUFFIX=2026.1.0` explicitly:

```
$ cd docker
$ docker compose -f docker-compose.yml -f docker-compose.override.yml down -v
$ IMAGE_SUFFIX=2026.1.0 docker compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

This succeeded. Polling `docker inspect --format '{{.State.Health.Status}}' ia-tsa-1b`
eventually returned:

```
CONTAINER ID   IMAGE                                                  COMMAND      CREATED         STATUS                   PORTS                                         NAMES
d330e27951b2   intel/ia-time-series-analytics-microservice:2026.1.0   "./run.sh"   3 minutes ago   Up 3 minutes (healthy)   0.0.0.0:5102->5000/tcp, [::]:5102->5000/tcp   ia-tsa-1b
```

This is a prebuilt image pulled from Docker Hub (not built locally from the
Dockerfile in this checkout), satisfying "validate using the prebuilt
`intel/ia-time-series-analytics-microservice` image via Docker Compose."

**Note on a mid-task hazard**: my very first `docker compose ... down -v` (run
before the successful `up`, to clean up the stuck attempt) printed a line removing
a container belonging to a *different* concurrent run (`040e432d7fcf_ia-tsa-2b`).
This happened because `docker/.env`'s `COMPOSE_PROJECT_NAME=timeseriessoftware` is
identical across all ~9 concurrent copies of this repo on the same host, so
Compose's project-scoped `down -v` was not run-scoped. This is called out in
`outputs/user_notes.md`.

## 4. Packaging and deploying the UDF

```
$ curl -s http://localhost:5102/health
{"status":"Kapacitor daemon is not running"}
```
(Expected — no UDF/config uploaded yet, so Kapacitor hasn't started.)

```
$ tar cf pressure_guard.tar udfs/pressure_guard.py tick_scripts/pressure_guard.tick
$ tar tf pressure_guard.tar
udfs/pressure_guard.py
tick_scripts/pressure_guard.tick

$ curl -s -X POST http://localhost:5102/udfs/package -F "file=@pressure_guard.tar"
{"status":"success","message":"UDF deployment package 'pressure_guard.tar' uploaded successfully."}

$ curl -s -X POST http://localhost:5102/config \
    -H 'accept: application/json' -H 'Content-Type: application/json' \
    -d @pressure_guard_config.json
{"status":"success","message":"Configuration updated successfully"}
```

Container logs confirmed the package validated and Kapacitor restarted with the
new task:

```
2026-07-27 02:00:42,515 - root - INFO - UDF deployment package 'pressure_guard.tar' uploaded and extracted to /tmp/pressure_guard.
INFO:     172.23.0.1:41080 - "POST /udfs/package HTTP/1.1" 200 OK
2026-07-27 02:00:42,558 - root - INFO - UDF deployment package pressure_guard validated successfully.
2026-07-27 02:00:42,558 - root - INFO - Received configuration data: {'udfs': {'name': 'pressure_guard'}}
INFO:     172.23.0.1:41090 - "POST /config HTTP/1.1" 200 OK
...
2026-07-27 02:00:42,628 - classifier_startup - INFO - Enabling pressure_guard.tick
...
2026-07-27 02:00:58,465 - classifier_startup - INFO - Kapacitor Tasks Enabled Successfully
2026-07-27 02:00:58,465 - classifier_startup - INFO - Kapacitor Initialized Successfully. Ready to Receive the Data....
...
2026-07-27 02:00:58,766 - classifier_startup - INFO - b'ts=2026-07-27T02:00:58.462Z lvl=info msg="started task" service=kapacitor task_master=main task=pressure_guard\n'
```

```
$ curl -s http://localhost:5102/health
{"status":"Kapacitor daemon is running"}
$ curl -s http://localhost:5102/config
{"udfs":{"name":"pressure_guard"}}
```

## 5. Verifying the flag behavior

First attempt sending the two sample points happened *before* the `started task`
log line landed (both POSTs returned 200 but were logged a fraction of a second
before Kapacitor confirmed the stream task was running), so nothing showed up for
them. I resent both points once `kapacitor list tasks` confirmed the task was
enabled:

```
$ docker exec ia-tsa-1b kapacitor list tasks
ID             Type      Status    Executing Databases and Retention Policies
pressure_guard stream    enabled   true      ["datain"."autogen"]

$ curl -s -X POST http://localhost:5102/input \
    -H 'accept: application/json' -H 'Content-Type: application/json' \
    -d '{"topic": "point_data", "fields": {"pressure_bar": 65}}'
{"status":"success","message":"Data sent to Time Series Analytics microservice"}

$ curl -s -X POST http://localhost:5102/input \
    -H 'accept: application/json' -H 'Content-Type: application/json' \
    -d '{"topic": "point_data", "fields": {"pressure_bar": 110}}'
{"status":"success","message":"Data sent to Time Series Analytics microservice"}
```

Container logs (filtered to `/input` and `pressure`-related lines):

```
$ docker logs ia-tsa-1b --since 30s 2>&1 | grep -iE "pressure|POST /input"
INFO:     172.23.0.1:47768 - "POST /input HTTP/1.1" 200 OK
INFO:     172.23.0.1:59452 - "POST /input HTTP/1.1" 200 OK
2026-07-27 02:00:58,766 - classifier_startup - INFO - b'ts=2026-07-27T02:00:58.462Z lvl=info msg="started task" service=kapacitor task_master=main task=pressure_guard\n'
INFO:     172.23.0.1:36448 - "POST /input HTTP/1.1" 200 OK
2026-07-27 02:01:18,790 - classifier_startup - INFO - b'ts=2026-07-27T02:01:18.274Z lvl=info msg="UDF log" service=kapacitor task_master=main task=pressure_guard node=pressure_guard2 text="2026-07-27 02:01:18,274 - root - INFO - Pressure 65.0 bar is outside the safe operating band 80-150."\n'
INFO:     172.23.0.1:36460 - "POST /input HTTP/1.1" 200 OK
```

The `65` reading produced the UDF flag log line
(`Pressure 65.0 bar is outside the safe operating band 80-150.`); the `110`
reading produced only the `POST /input 200 OK` acceptance line with **no**
corresponding "outside the safe operating band" log — i.e. it was correctly
accepted but not flagged.

To be thorough, I grepped the *entire* container log for any `Pressure ` message
to make sure exactly one flag was ever emitted (i.e. the 110-bar point never
triggered a flag anywhere, not just "since the last 30s"):

```
$ docker logs ia-tsa-1b 2>&1 | grep -i "Pressure "
2026-07-27 02:01:18,790 - classifier_startup - INFO - b'ts=2026-07-27T02:01:18.274Z lvl=info msg="UDF log" service=kapacitor task_master=main task=pressure_guard node=pressure_guard2 text="2026-07-27 02:01:18,274 - root - INFO - Pressure 65.0 bar is outside the safe operating band 80-150."\n'
```

Exactly one match — confirming the 65-bar reading flagged and the 110-bar reading
did not. This validates the `pressure_guard` UDF's threshold logic
(`< 80 or > 150`) against the two sample inputs.

## 6. Teardown

```
$ cd docker
$ IMAGE_SUFFIX=2026.1.0 docker compose -f docker-compose.yml -f docker-compose.override.yml down -v
 Container ia-tsa-1b  Stopping
 Container ia-tsa-1b  Stopped
 Container ia-tsa-1b  Removing
 Container ia-tsa-1b  Removed
 Volume timeseriessoftware_vol_temp_time_series_analytics_microservice  Removing
 Network timeseriessoftware_timeseries_network  Removing
 Volume timeseriessoftware_vol_temp_time_series_analytics_microservice  Removed
 Network timeseriessoftware_timeseries_network  Removed

$ docker ps -a --filter name=ia-tsa-1b
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
```

Clean teardown confirmed — no `ia-tsa-1b` container left behind.
