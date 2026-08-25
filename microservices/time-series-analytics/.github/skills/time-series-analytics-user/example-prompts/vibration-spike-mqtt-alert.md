Build a UDF that detects sudden vibration spikes on a motor and publishes an MQTT alert when one occurs, using the Time Series Analytics microservice.

- Field `vibration_mm_s` arrives via `POST /input`; flag a point if it jumps more than 5 mm/s from the previous reading.
- Use the rate-of-change pattern (references/patterns.md) — needs a `previous_value` instance attribute, no model file.
- Wire the flagged output to Kapacitor's native MQTT alert node (`|alert()...mqtt(...).brokerName(...)`) per references/tickscript-basics.md, assuming `config.json`'s `alerts.mqtt` names the broker `motor_alerts_broker`.
- Name the UDF `vibration_spike_detector`.
- An MQTT broker (e.g. `eclipse-mosquitto`) must be reachable from the microservice container on the same Docker network, at the host/port set in `config.json`'s `alerts.mqtt.mqtt_broker_host`/`mqtt_broker_port` — start one if none is already running.

Validate the application using:
- The prebuilt `intel/ia-time-series-analytics-microservice` image via Docker Compose, with `alerts.mqtt` configured in `config.json`.
- Sample sequence sent to `POST /input`: `vibration_mm_s` = 2.0, then 2.1, then 9.5 (the jump from 2.1 to 9.5 should flag), then 9.6 (should not flag — small delta from the now-elevated baseline).
- Actually subscribe to the alert topic on the broker (e.g. `docker exec <broker_container> mosquitto_sub -h localhost -t '<topic>' -v`) and confirm exactly one message arrives, for the 2.1 -> 9.5 point — don't just check that `POST /config`/`POST /udfs/package` returned success or that the task enabled; neither proves an alert was actually published.

Expected results:
- `vibration_spike_detector.py` tracks `previous_value` across calls and only flags the 2.1 -> 9.5 transition.
- The generated tick script chains `|alert().crit(lambda: TRUE).mqtt('<topic>').brokerName('motor_alerts_broker')` off the UDF node. Two easy-to-miss requirements, confirmed by an actual run of this prompt:
  - `.mqtt(...)`'s argument is the MQTT **topic**, not the broker name — the broker is selected via a separate, chained `.brokerName('motor_alerts_broker')` (must match `alerts.mqtt.name` in `config.json`). Omitting `.brokerName(...)` silently falls back to whichever broker config has `default=true` and treats the string passed to `.mqtt(...)` as the topic instead — this produces no error anywhere and is easy to mistake for working.
  - `alert()` needs at least one severity-level lambda (`.info()`/`.warn()`/`.crit()`) to ever dispatch to a handler — without one, every point is implicitly `OK` and MQTT never fires, even with the broker/topic wired correctly. Since every point reaching this alert node is already a flagged anomaly, `.crit(lambda: TRUE)` is sufficient.
- Re-running the validation sequence without redeploying (restarting) the task will carry over `previous_value` from the prior run — expect the first point of a fresh run to also potentially flag relative to that stale state; restart the task (`POST /config?restart=true`) before each clean validation run.
- In the final answer, include the exact `POST /udfs/package` and
  `POST /config`/`POST /config?restart=true` response bodies, quote the exact
  broker-side `mosquitto_sub` output showing the single alert for 9.5, and
  explicitly state that no second MQTT message arrived for 9.6.
- Also quote:
  - the exact UDF field/state lines proving it reads `point.fieldsDouble["vibration_mm_s"]`
    and tracks `self.previous_value`
  - the exact TICKscript alert chain line showing
    `@vibration_spike_detector() |alert().crit(lambda: TRUE).mqtt(...).brokerName('motor_alerts_broker')`
