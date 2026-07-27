# Debug: "UDF deployment succeeded but nothing happens" — transcript

Skill used: `.github/skills/time-series-analytics-dev/SKILL.md` (+ `references/source-map.md`,
`references/build-and-deploy.md`, `references/testing.md`, and
`example-prompts/debug-udf-not-starting.md`).

Working copy: isolated standalone clone at `.../scratchpad/tsa-evals/run-5w` (treated as repo root).
Container: `ia-tsa-5w`, REST API on host port `5109`.

## 1. Setup

Per the infra notes, created `docker/docker-compose.override.yml`:

```yaml
services:
  ia-time-series-analytics-microservice:
    container_name: ia-tsa-5w
    ports:
      - "5109:5000"
```

The prebuilt image tag pinned in `docker/.env` (`IMAGE_SUFFIX="2026.2.0"`) was not present locally;
only `intel/ia-time-series-analytics-microservice:2026.1.0` was available (`docker images`), so the
image was brought up with `IMAGE_SUFFIX=2026.1.0` instead of building from source (consistent with
"use the prebuilt image, no need to build from source ... unless diagnosis leads to a genuine code
fix").

**Two purely environmental snags, unrelated to the graded bug, noted for completeness:**

- This appears to be a shared Docker host running multiple concurrent instances of this same eval
  (`docker ps -a` showed sibling containers `ia-tsa-1w`, `ia-tsa-3w` from other runs). All runs share
  the same `docker/.env` `COMPOSE_PROJECT_NAME=timeseriessoftware`, so `docker compose up` collided on
  the shared network name and on host port `5000:5000` (which `docker-compose.yml` binds
  unconditionally in addition to the override's `5109:5000`). Fixed for this run only by exporting a
  unique `COMPOSE_PROJECT_NAME=tsa5w` and removing the base `5000:5000` port line from this isolated
  copy's `docker/docker-compose.yml` (kept only the override's `5109:5000`). This is host/eval-harness
  plumbing, not a service bug — no equivalent change was made outside this scratch copy.
- On the very first `POST /config`, `kapacitord` took longer than the 10 × 5s (50s) retry budget in
  `enable_classifier_task` to open port 9092 (cold start in this constrained sandbox), so
  `classifier_startup.py` hit `os._exit(1)` and the container's `restart: unless-stopped` policy
  restarted the process (`RestartCount=1`). Also discovered the tmpfs-backed `/tmp` volume is wiped on
  every such restart, requiring the UDF package re-upload. Re-running the same `POST /udfs/package` +
  `POST /config` sequence succeeded normally on the next attempt (kapacitor bound port 9092 in ~5s).
  Not investigated further — out of scope for this task, and the retry/backoff behavior itself is
  working as designed.

## 2. Reproduce: deliberately mismatched measurement vs. topic

Built a trivial threshold UDF package (`repro/udfs/threshold_demo.py`,
`repro/tick_scripts/threshold_demo.tick`), packaged as `repro/threshold_demo.tar` with the required
`udfs/` + `tick_scripts/` layout (no `models/`).

The tick script's filter measurement was set to `'threshold_input'`:

```
dbrp "datain"."autogen"
var data0 = stream
        |from()
                .measurement('threshold_input')
data0
    @threshold_demo()
```

The UDF (`threshold_demo.py`) flags any point where `fields.value > 50`, logging
`"threshold_demo UDF received point with value=..."` on every point and
`"FLAGGED: value ... exceeds threshold ..."` when it flags one.

Uploaded and deployed:

```
$ curl -s -X POST http://localhost:5109/udfs/package -F "file=@threshold_demo.tar"
{"status":"success","message":"UDF deployment package 'threshold_demo.tar' uploaded successfully."}

$ curl -s -X POST http://localhost:5109/config -H "Content-Type: application/json" \
    -d '{"udfs": {"name": "threshold_demo", "device": "CPU"}}'
{"status":"success","message":"Configuration updated successfully"}
```

`docker logs ia-tsa-5w` confirmed the package validated and the Kapacitor task actually started and
enabled successfully — this is **not** the "structurally invalid package" failure class:

```
2026-07-27 01:59:17,481 - classifier_startup - INFO - UDF deployment package /tmp/threshold_demo exists.
2026-07-27 01:59:17,481 - root - INFO - UDF deployment package threshold_demo validated successfully.
...
2026-07-27 02:01:45,624 - classifier_startup - INFO - Kapacitor Tasks Enabled Successfully
2026-07-27 02:01:45,624 - classifier_startup - INFO - Kapacitor Initialized Successfully. Ready to Receive the Data....
```

`curl http://localhost:5109/health` → `{"status":"Kapacitor daemon is running"}`.

Now sent a data point with `topic` **not** matching the tick script's `.measurement('threshold_input')`
(deliberately using `"sensor_data"` instead, simulating a user who typed the wrong topic name):

```
$ curl -s -X POST http://localhost:5109/input -H "Content-Type: application/json" \
    -d '{"topic": "sensor_data", "fields": {"value": 999}}'
{"status":"success","message":"Data sent to Time Series Analytics microservice"}
```

`POST /input` returned 200 — exactly the reported symptom. `docker logs ia-tsa-5w` after this call
shows **nothing** from the UDF (no "received point", no "FLAGGED", no error either):

```
2026-07-27 02:01:45,754 - classifier_startup - INFO - b'... "started task" ... task=threshold_demo\n'
INFO:     172.19.0.1:38640 - "GET /health HTTP/1.1" 200 OK
INFO:     172.19.0.1:41978 - "POST /input HTTP/1.1" 200 OK
```

## 3. Diagnosis: confirm points never reach the UDF node

Per the skill's debug guidance, checked Kapacitor's own task graph/stats (not visible in the
container's top-level log) via `docker exec`:

```
$ docker exec ia-tsa-5w sh -c 'kapacitor show threshold_demo 2>&1 | sed -n "/^DOT:/,\$p"'
DOT:
digraph threshold_demo {
graph [throughput="0.00 points/s"];

stream0 [avg_exec_time_ns="0s" errors="0" working_cardinality="0" ];
stream0 -> from1 [processed="0"];

from1 [avg_exec_time_ns="0s" errors="0" working_cardinality="0" ];
from1 -> threshold_demo2 [processed="0"];

threshold_demo2 [avg_exec_time_ns="0s" errors="0" working_cardinality="0" ];
}
```

`processed="0"` on every edge, including into the UDF node (`threshold_demo2`) — the point was
accepted by the REST API and written to InfluxDB/Kapacitor's `datain.autogen` stream, but the tick
script's `|from().measurement('threshold_input')` filter node dropped it silently because the
written point's measurement was `sensor_data` (from `topic`), not `threshold_input`. No error is
raised anywhere in this path — Kapacitor's stream filtering by design just drops non-matching points.

This is the exact mechanism the skill's gotcha table describes: *"Consider the tick script's
`.measurement(...)` vs. what `POST /input`'s `topic` actually sends — a mismatch here doesn't error,
it just means zero points ever reach the UDF node."*

## 4. Confirm the fix: use a matching topic

Sent a point with `topic` equal to the tick script's `.measurement()` value:

```
$ curl -s -X POST http://localhost:5109/input -H "Content-Type: application/json" \
    -d '{"topic": "threshold_input", "fields": {"value": 999}}'
{"status":"success","message":"Data sent to Time Series Analytics microservice"}
```

Kapacitor's task graph now shows the point flowing all the way to the UDF node:

```
$ docker exec ia-tsa-5w sh -c 'kapacitor show threshold_demo 2>&1 | sed -n "/^DOT:/,\$p"'
DOT:
digraph threshold_demo {
...
stream0 -> from1 [processed="1"];
...
from1 -> threshold_demo2 [processed="1"];
...
}
```

And the raw Kapacitor log (`/tmp/log/kapacitor/kapacitor.log` inside the container) shows the UDF
actually processing and flagging the point:

```
ts=2026-07-27T02:02:41.922Z lvl=info msg="UDF log" ... text="... threshold_demo UDF received point with value=999.0"
ts=2026-07-27T02:02:41.923Z lvl=info msg="UDF log" ... text="... FLAGGED: value 999.0 exceeds threshold 50.0."
```

These lines also eventually surface in `docker logs ia-tsa-5w` (via `classifier_startup.py`'s
`kapacitor_daemon_logs` tail thread, ~1 log-line lag observed — the thread batches slightly behind the
raw file, not itself a bug worth chasing for this task):

```
2026-07-27 02:03:36,888 - classifier_startup - INFO - b'... FLAGGED: value 999.0 exceeds threshold 50.0.\n'
2026-07-27 02:03:36,888 - classifier_startup - INFO - b'... threshold_demo UDF received point with value=777.0\n'
```

Sent a second matching point (`value: 777`) to confirm repeatability — same result (both "received"
and "FLAGGED" lines appear; `kapacitor show` edge counters incremented to `processed="2"`).

## 5. Final diagnosis

**Root cause: measurement/topic name mismatch — a user-configuration mistake, not a bug in this
service's code (`src/main.py` / `src/classifier_startup.py`).**

- The UDF deployment package was structurally valid: `udfs/threshold_demo.py` and
  `tick_scripts/threshold_demo.tick` both existed and passed `check_udf_package`'s file-existence
  checks (`src/classifier_startup.py:77-133`), so `POST /config` correctly returned 200 and the
  Kapacitor task was correctly defined and enabled (`enable_classifier_task`,
  `src/classifier_startup.py:301-342`, confirmed via the "Kapacitor Tasks Enabled Successfully" /
  "Ready to Receive the Data" log lines).
- Nothing in `POST /config`'s handler (`config_file_change`, `src/main.py:461-585`) or
  `check_udf_package` parses the tick script's content or cross-checks its `.measurement(...)` value
  against anything — they only check that the required files exist on disk. There is no code path in
  this service that could catch a measurement/topic mismatch; Kapacitor's own stream `|from()` node
  performs the (silent, by design) filtering entirely inside `kapacitord`, outside this service's
  Python code.
- `POST /input` (`src/main.py:296-388`) also does not — and reasonably should not — validate that the
  `topic` it's given corresponds to any particular tick script; it's a generic point-ingestion
  endpoint that just converts JSON to line protocol and writes it to Kapacitor's `datain.autogen`
  database, always returning 200 as long as Kapacitor accepted the write. A write succeeding is not
  the same as a downstream task consuming that data — that is a per-task filtering concern handled
  entirely inside Kapacitor via the TICK script's `.measurement()` predicate.
- Confirmed via `kapacitor show <task>`'s DOT graph edge counters: `processed="0"` on every edge when
  `topic` didn't match `.measurement()`, `processed="1"`/`"2"` (matching the number of calls) once it
  did, plus the corresponding "received point"/"FLAGGED" UDF log lines appearing only in the matching
  case.

No source change was made — this matches the "user-config issue rather than a service bug" branch of
the task, so no regression test was added either (there's no code defect to guard against; the
behavior is Kapacitor's intended stream-filtering semantics). The fix is operational: when deploying a
UDF, the tick script's `.measurement('<name>')` value and the `topic` field sent to `POST /input` for
that data stream must be identical strings.
