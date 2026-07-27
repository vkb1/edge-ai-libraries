<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Common Use-Case Patterns (Fast Path)

Match the user's description to a row below before writing a UDF from
scratch. Each pattern is a small delta on
[`../assets/udf_stream_template.py`](../assets/udf_stream_template.py) — the
`__init__` state and the body of `point()` are the only things that change.
Confirm the specific parameters (field name, thresholds, window size, model
file) with the user before generating code; don't guess numeric thresholds.

| Pattern | Use when the user wants to... | Needs a model file? |
|---|---|---|
| [Threshold / range check](#threshold--range-check) | flag values outside a fixed `[low, high]` band | No |
| [Rate-of-change / spike](#rate-of-change--spike-detection) | flag sudden jumps between consecutive readings | No |
| [Rolling-window statistics](#rolling-window-statistics-z-score) | flag statistical outliers relative to recent history | No (optional) |
| [Pretrained model inference](#pretrained-model-inference) | run a trained scikit-learn classifier/regressor/anomaly detector per point | Yes |

If none of these fit (e.g. multi-field correlation, sequence modeling,
custom windowing logic), fall back to
[`udf-authoring.md`](udf-authoring.md) and write the `point()` body from
first principles — the method contract and state model are the same either
way.

## Threshold / Range Check

The simplest pattern, and what the microservice's built-in sample
(`udfs/temperature_classifier.py`) does. No `__init__` state needed.

```python
LOW, HIGH = 20.0, 25.0   # confirm actual bounds with the user

def point(self, point):
    value = point.fieldsDouble.get("value")
    if value is None:
        logger.error("Expected double field 'value' missing from point")
        return
    if value < LOW or value > HIGH:
        response = udf_pb2.Response()
        response.point.CopyFrom(point)
        self._agent.write_response(response, True)
```

## Rate-of-Change / Spike Detection

Flags points where the change from the previous reading exceeds a
threshold. Needs one instance attribute.

```python
def __init__(self, agent):
    self._agent = agent
    self.previous_value = None

def point(self, point):
    value = point.fieldsDouble.get("value")
    if value is None:
        return
    if self.previous_value is not None:
        delta = abs(value - self.previous_value)
        if delta > THRESHOLD:   # confirm THRESHOLD with the user
            response = udf_pb2.Response()
            response.point.CopyFrom(point)
            self._agent.write_response(response, True)
    self.previous_value = value   # update regardless of anomaly status
```

## Rolling-Window Statistics (Z-Score)

Flags points that deviate from the recent mean by more than N standard
deviations. Needs a bounded window; `collections.deque(maxlen=...)` is the
simplest correct choice since it evicts automatically.

```python
import collections
import statistics

WINDOW_SIZE = 30    # confirm with the user
Z_THRESHOLD = 3.0

def __init__(self, agent):
    self._agent = agent
    self.window = collections.deque(maxlen=WINDOW_SIZE)

def point(self, point):
    value = point.fieldsDouble.get("value")
    if value is None:
        return
    if len(self.window) >= WINDOW_SIZE // 2:  # need enough history to be meaningful
        mean = statistics.fmean(self.window)
        stdev = statistics.pstdev(self.window) or 1e-9
        z = (value - mean) / stdev
        if abs(z) > Z_THRESHOLD:
            response = udf_pb2.Response()
            response.point.CopyFrom(point)
            response.point.fieldsDouble["z_score"] = z
            self._agent.write_response(response, True)
    self.window.append(value)
```

For anything past a simple z-score (rolling PCA reconstruction error,
seasonal decomposition), Intel® Extension for Scikit-learn* is preinstalled
and can accelerate the heavier variants — treat this as the "pretrained
model" pattern instead once you're fitting anything.

## Pretrained Model Inference

For a model already trained offline (scikit-learn classifier, regressor,
`IsolationForest`, `OneClassSVM`, etc.), serialize it with `joblib` or
`pickle`, place the file under `models/` in the deployment package (named
starting with `<udf_name>`), and set `config.json`'s `udfs.models` to that
filename. See [`udf-authoring.md#model-loading`](udf-authoring.md#model-loading)
for the env vars this makes available.

```python
import os
import joblib

MODEL_PATH = os.environ.get("MODEL_PATH")

def __init__(self, agent):
    self._agent = agent
    self.model = joblib.load(MODEL_PATH) if MODEL_PATH else None

def point(self, point):
    value = point.fieldsDouble.get("value")
    if value is None or self.model is None:
        return
    prediction = self.model.predict([[value]])[0]
    if prediction == -1:   # convention for e.g. IsolationForest: -1 = anomaly
        response = udf_pb2.Response()
        response.point.CopyFrom(point)
        self._agent.write_response(response, True)
```

Multi-feature models: read each input field via `point.fieldsDouble.get(...)`
and assemble the feature vector in the same order the model was trained on
— get that ordering from the user or the model's training code, don't
assume.

To run inference on Intel iGPU instead of CPU, set `config.json`'s
`udfs.device` to `"GPU"` (or `"GPU:N"` for a specific device) — the
resolved value arrives as the `DEVICE` env var.
