Build a UDF that flags hydraulic pressure readings outside a safe operating band, using the Time Series Analytics microservice.

- Field `pressure_bar` arrives via `POST /input`; flag any reading below 80 or above 150.
- Use the threshold pattern (references/patterns.md) — no model file needed.
- Name the UDF `pressure_guard`; deploy it and confirm flagged points show up in the container logs.

Validate the application using:
- The prebuilt `intel/ia-time-series-analytics-microservice` image via Docker Compose.
- Sample input points: `{"topic": "point_data", "fields": {"pressure_bar": 65}}` (should flag) and `{"topic": "point_data", "fields": {"pressure_bar": 110}}` (should not flag).

Expected results:
- `pressure_guard.py`, `pressure_guard.tick`, and a `pressure_guard.tar` deployment package are created with matching names throughout.
- After `POST /udfs/package` + `POST /config`, the 65 bar point appears as a flagged/logged anomaly and the 110 bar point does not.
- In the final answer, include the exact `POST /udfs/package` and `POST /config`
  response bodies, quote the exact flagged container log line for
  `pressure_bar=65`, and quote the received/log context proving
  `pressure_bar=110` did not produce a later `Flagged anomalous point` line.
- Also quote:
  - the exact UDF field-read line proving it reads `point.fieldsDouble["pressure_bar"]`
  - the exact config JSON posted showing `"udfs": {"name": "pressure_guard"}`
