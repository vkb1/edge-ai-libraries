<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# UDF Authoring Contract

A UDF is a small, long-lived Python process that Kapacitor spawns per
enabled task and feeds points to over stdin/stdout using a protobuf
protocol. The `kapacitor.udf.agent` package (vendored into the image at
`/app/kapacitor_python/`) hides that protocol behind a `Handler` base class
you subclass. Start from
[`../assets/udf_stream_template.py`](../assets/udf_stream_template.py)
rather than writing this from scratch.

## The methods Kapacitor calls

```python
from kapacitor.udf.agent import Agent, Handler
from kapacitor.udf import udf_pb2
```

| Method | Called when | What to return |
|---|---|---|
| `info()` | once, at startup | `response.info.wants = udf_pb2.STREAM` and `.provides = udf_pb2.STREAM` — this microservice's REST ingestion (`POST /input`) always produces a point stream, so stream-in/stream-out is the right choice for nearly every use case here |
| `init(init_req)` | once, when the task is enabled | `response.init.success = True`, or `False` + `.init.error = "..."` to abort task startup |
| `point(point)` | once per incoming point | nothing required; call `self._agent.write_response(...)` to emit a point downstream (see below) |
| `snapshot()` / `restore(restore_req)` | around daemon restarts | most deployments return an empty snapshot and an unimplemented restore, since `config.json` is reapplied fresh on every container restart anyway |
| `begin_batch(begin_req)` / `end_batch(end_req)` | only for BATCH tasks | leave raising `Exception("not supported")` unless you specifically switched `info()` to BATCH |

## Reading a point's fields

The `fields` dict you send to `POST /input` becomes typed attributes on the
`point` object, keyed by field name, with the Python-JSON type determining
which one:

```python
value = point.fieldsDouble.get("value")   # JSON number -> fieldsDouble
count = point.fieldsInt.get("count")      # JSON int -> fieldsInt (rare; JSON numbers usually parse as double)
label = point.fieldsString.get("label")
flag  = point.fieldsBool.get("flag")
```

Tags sent under `POST /input`'s `tags` key show up on `point.tags` (a
string-keyed dict) if you need to branch on them.

## Emitting a result

To flag a point (anomaly, classification result, whatever your pattern
produces), copy it into a `Response` and write it back through the agent —
this is what makes the point visible to anything chained after your UDF
node in the tick script (see
[`tickscript-basics.md`](tickscript-basics.md)):

```python
response = udf_pb2.Response()
response.point.CopyFrom(point)
self._agent.write_response(response, True)
```

You're not limited to mirroring the input point — you can set
`response.point.fieldsDouble["score"] = ...` etc. before writing it back, to
attach a derived value (e.g. an anomaly score or z-score) rather than just
the raw point.

## State across points

Kapacitor keeps **one UDF process alive per enabled task**, not one per
point — so instance attributes on your `Handler` subclass persist across
`point()` calls for the life of the task. This is exactly what
rolling-window statistics, rate-of-change tracking, or a loaded model need:

```python
def __init__(self, agent):
    self._agent = agent
    self.previous_value = None            # rate-of-change pattern
    self.window = collections.deque(maxlen=30)   # rolling-stats pattern
```

## Model loading

`config.json`'s `udfs.models`/`udfs.device` fields are documented field-by-field
in [Configure Microservice](https://github.com/open-edge-platform/edge-ai-libraries/blob/main/microservices/time-series-analytics/docs/user-guide/how-to-configure.md);
what that doc doesn't cover is the runtime contract your UDF process sees.
If `udfs.models` names a file, and that file is placed under `models/` in
your deployment package (named starting with `<udf_name>`), the
microservice mounts it and exposes two environment variables to your UDF
process:

- `MODEL_PATH` — full path to the model file
- `DEVICE` — `"auto"` (CPU) or `"GPU"` / `"GPU:N"`, resolved from
  `udfs.device` in `config.json`

Load the model once in `__init__`, never per-point:

```python
import os, joblib
MODEL_PATH = os.environ.get("MODEL_PATH")

class Handler(...):
    def __init__(self, agent):
        self._agent = agent
        self.model = joblib.load(MODEL_PATH) if MODEL_PATH else None
```

Intel® Extension for Scikit-learn* (`scikit-learn-intelex`) is preinstalled
in the image, so a scikit-learn-compatible model's `.predict()` /
`.decision_function()` calls can transparently target the Intel iGPU when
`DEVICE` is `"GPU"` — no code change needed beyond honoring the env var if
your model-loading code patches in the extension explicitly.

## Dependencies beyond the base image

An optional `udfs/requirements.txt` in your deployment package gets
`pip install --target`-ed into a directory that's prepended to
`PYTHONPATH` before your UDF process starts. Use it for anything beyond
what's already in the image (numpy and scikit-learn-intelex are already
present).

## Logging

Anything your UDF process writes to stderr via the standard `logging`
module is captured into Kapacitor's own log
(`/tmp/log/kapacitor/kapacitor.log` inside the container) — this is your
primary debugging tool once the task is deployed; see
[`api-workflow.md`](api-workflow.md#troubleshooting).

## The one gotcha to know first

The three names — `udfs.name` in `config.json`, the `.py` filename under
`udfs/`, and the `.tick` filename under `tick_scripts/` — must all be
character-for-character identical, and the tick script's UDF node
(`@<name>()`) must reference that same name. The microservice generates the
Kapacitor `[udf.functions.<name>]` registration from these at startup; any
mismatch fails silently at the wiring level (the task enables, but points
never reach your code) or loudly at `POST /config` time ("UDF deployment
package validation failed for `<name>`"). [`package_udf.sh`](../scripts/package_udf.sh)
checks this for you before upload.
