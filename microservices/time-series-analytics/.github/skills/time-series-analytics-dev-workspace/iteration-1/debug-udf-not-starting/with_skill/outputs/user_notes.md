# Notes / ambiguities encountered

- **Concurrent eval runs share Docker state.** This host was running multiple parallel copies of
  this same eval (sibling containers `ia-tsa-1w`, `ia-tsa-3w` visible in `docker ps -a`), and all of
  them source the same `docker/.env` with a fixed `COMPOSE_PROJECT_NAME=timeseriessoftware`. That
  makes `docker compose up` collide on the shared network name and, more seriously, on host port
  `5000` — the base `docker-compose.yml` maps `5000:5000` *unconditionally*, in addition to whatever
  the override adds. The infra note's override snippet (container_name + port 5109 only) doesn't
  neutralize that base `5000:5000` mapping, since Compose concatenates `ports:` lists across files
  rather than replacing them. I worked around this only inside my isolated scratch copy by (a) using
  `COMPOSE_PROJECT_NAME=tsa5w` for this run's compose invocations, and (b) removing the base
  `5000:5000` line from this copy's `docker/docker-compose.yml`. If this infra pattern is reused for
  future evals with true parallelism, the instructions may want to either assign each run a unique
  `COMPOSE_PROJECT_NAME` up front, or have the override explicitly clear the base ports list.

- **Prebuilt image tag mismatch.** `docker/.env` pins `IMAGE_SUFFIX="2026.2.0"`, but only
  `intel/ia-time-series-analytics-microservice:2026.1.0` was present locally (`docker images`). I
  used `IMAGE_SUFFIX=2026.1.0` on the compose command line rather than pulling/building, per "use the
  prebuilt image ... unless your diagnosis leads you to a genuine code fix." This didn't affect the
  diagnosis (no source-level fix was needed), but it's worth flagging in case `2026.2.0` behaves
  differently.

- **First-boot flakiness, not the graded bug.** On the very first `POST /config`, `kapacitord` took
  longer than the built-in 50-second retry budget to open port 9092 in this sandboxed environment,
  triggering an automatic `os._exit(1)` + container restart. This looked alarming at first (empty
  `docker logs` for a while, `kapacitord` reachable only after `docker exec` inspection) but resolved
  itself on retry and is unrelated to the measurement/topic mismatch this task asked me to reproduce.
  I documented it in `transcript.md` for completeness but did not chase it as a bug, since the task
  scope is specifically the silent measurement/topic mismatch.

- **No source fix was made.** The task said to "fix or clearly explain the root cause." Since this
  reproduced cleanly as a user-configuration mismatch (tick script `.measurement()` vs. `POST /input`
  `topic`) with no code path in `src/main.py` or `src/classifier_startup.py` that could plausibly
  catch it — the mismatch is resolved entirely inside `kapacitord`'s own stream filtering, outside
  this service's Python code — I treated this as the "identify it as a user-config issue rather than
  a service bug" branch explicitly allowed by the task, and did not add a regression test (there is
  no code defect to regression-test against). If the intent was instead for the service to proactively
  detect/warn about such mismatches at `POST /config` time (e.g., by parsing the tick script and
  cross-checking its `.measurement()` value against some expected topic), that would be a scope-adding
  feature request rather than a bug fix, and I did not implement it absent an explicit ask.
