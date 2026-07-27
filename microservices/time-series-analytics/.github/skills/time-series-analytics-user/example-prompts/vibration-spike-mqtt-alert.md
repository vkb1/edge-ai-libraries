Build a UDF that detects sudden vibration spikes on a motor and publishes an MQTT alert when one occurs, using the Time Series Analytics microservice.

- Field `vibration_mm_s` arrives via `POST /input`; flag a point if it jumps more than 5 mm/s from the previous reading.
- Use the rate-of-change pattern (references/patterns.md) — needs a `previous_value` instance attribute, no model file.
- Wire the flagged output to Kapacitor's native MQTT alert node (`|alert()...mqtt(...)`) per references/tickscript-basics.md, assuming `config.json`'s `alerts.mqtt` names the broker `motor_alerts_broker`.
- Name the UDF `vibration_spike_detector`.

Validate the application using:
- The prebuilt `intel/ia-time-series-analytics-microservice` image via Docker Compose, with `alerts.mqtt` configured in `config.json`.
- Sample sequence sent to `POST /input`: `vibration_mm_s` = 2.0, then 2.1, then 9.5 (the jump from 2.1 to 9.5 should flag), then 9.6 (should not flag — small delta from the now-elevated baseline).

Expected results:
- `vibration_spike_detector.py` tracks `previous_value` across calls and only flags the 2.1 -> 9.5 transition.
- The generated tick script chains `|alert().mqtt('motor_alerts_broker')` off the UDF node, matching the broker name in `config.json`.
