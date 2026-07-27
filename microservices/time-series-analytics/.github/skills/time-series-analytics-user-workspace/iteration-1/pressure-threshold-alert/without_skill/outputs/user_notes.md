# Notes on ambiguity / guesses made

- **Field type for `pressure_bar`**: the task's sample payloads
  (`{"fields": {"pressure_bar": 65}}`) are JSON integers, but the service converts
  input to InfluxDB line protocol (`json_to_line_protocol` in `src/main.py`), where
  a bare number like `65` is written unquoted, which InfluxDB line protocol treats
  as a **float** unless suffixed with `i`. The docs' own example
  (`temperature_classifier.py`) only reads `point.fieldsDouble["temperature"]`. To
  be safe, `pressure_guard.py` checks both `point.fieldsDouble["pressure_bar"]`
  and `point.fieldsInt["pressure_bar"]`. In practice, the observed log line was
  `Pressure 65.0 bar is outside...` — confirming it did arrive as a float via
  `fieldsDouble`, so the `fieldsInt` fallback wasn't exercised but is kept as a
  defensive guess in case a caller sends an explicitly-integer field (e.g. `65i` in
  line protocol).

- **No `config.json` in the repo was overwritten.** The repo ships a top-level
  `config.json` pointing at `temperature_classifier`. Rather than edit that
  in-place (which is the microservice's *default/build-time* config, loaded only
  if the container starts with no runtime config posted), I created a separate
  `pressure_guard_config.json` and activated the new UDF purely via the runtime
  `POST /config` API, matching how the get-started guide itself layers a new UDF
  on top of the default. This was a judgment call — the task didn't say whether to
  edit `config.json` in place or POST a new config; POSTing seemed more faithful to
  "deploy against a running instance."

- **`docker/.env`'s `IMAGE_SUFFIX="2026.2.0"` does not exist on Docker Hub.** I
  confirmed this with `docker manifest inspect
  intel/ia-time-series-analytics-microservice:2026.2.0` → `no such manifest`. I
  used `IMAGE_SUFFIX=2026.1.0` instead (confirmed to exist both on the registry and
  already pulled locally). This wasn't specified by the task ("prebuilt
  intel/ia-time-series-analytics-microservice image" with no version pin), so I
  picked the newest tag that actually resolves. This should be flagged to whoever
  maintains `docker/.env` in this repo checkout.

- **Race condition between "task enabled" and first data point.** The `/config`
  POST triggers Kapacitor restart + TICK task enable asynchronously
  (`background_tasks.add_task(restart_kapacitor)`), and `/health` reporting
  "running" doesn't guarantee the specific stream task has finished subscribing.
  My first two `POST /input` calls (sent immediately after `/health` turned
  "running") landed a fraction of a second *before* the log line
  `"started task" ... task=pressure_guard`, and produced no UDF log output at all
  (points were seemingly dropped rather than queued, since stream tasks only see
  live data). I only discovered this by diffing `docker logs` timestamps
  carefully. The task description doesn't mention this race, so I added an
  explicit `kapacitor list tasks` check (status `enabled`) before resending the
  two sample points, which then worked as expected. Anyone following the
  get-started doc's literal curl sequence with tight timing could hit the same
  silent drop.

- **Shared `COMPOSE_PROJECT_NAME` across concurrent runs.** `docker/.env` hardcodes
  `COMPOSE_PROJECT_NAME=timeseriessoftware`, identical across every copy of this
  repo used for the ~9 concurrent evaluation runs on this host. This means
  Compose-managed resources (network name `timeseriessoftware_timeseries_network`,
  volume name `timeseriessoftware_vol_temp_time_series_analytics_microservice`) are
  **not** run-scoped by the override the task instructions gave (which only
  overrides `container_name` and `ports`). During my first (aborted) `down -v`
  cleanup, I observed Compose remove a container belonging to a different
  concurrent run (`040e432d7fcf_ia-tsa-2b`) that happened to be in the same
  Compose project. This is a real collision risk in the given infra setup that I
  could not fully avoid without deviating from the literal infra instructions
  (which named an exact `docker-compose.override.yml` content). I did not set a
  unique `COMPOSE_PROJECT_NAME` myself since the task instructions specified the
  override file's exact contents; flagging this for whoever designed the
  concurrent-run harness.

- **`ports: !override` YAML tag**: the infra note's override snippet
  (`ports: - "5102:5000"`) would, under plain Compose merge semantics, be
  *concatenated* with the base file's `- 5000:5000`, publishing both ports and
  risking a `5000:5000` bind collision with other concurrent runs. I added the
  Compose-spec `!override` merge tag to make the override list *replace* rather
  than append, verified via `docker compose config`. This is a deviation from the
  literal text of the infra note (which showed plain YAML) but preserves its
  stated intent ("ports must not collide"); flagging in case the harness expects
  the override file byte-for-byte.
