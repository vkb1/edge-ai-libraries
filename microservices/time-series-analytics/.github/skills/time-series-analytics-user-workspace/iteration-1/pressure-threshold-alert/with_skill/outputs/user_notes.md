# Notes on skill accuracy / ambiguities encountered

## 1. `IMAGE_SUFFIX` in `docker/.env` pointed at a nonexistent tag

`docker/.env` shipped with `IMAGE_SUFFIX="2026.2.0"`, but that tag does
not exist on Docker Hub for `intel/ia-time-series-analytics-microservice`
(`docker compose pull` returned `manifest unknown`). The skill's own
step 1 anticipates this ("If `docker compose pull` can't find the tag,
check available tags... and set `IMAGE_SUFFIX` accordingly") and that
guidance worked — `2026.1.0` was available and is what got used. This
isn't a skill bug, just worth flagging that the repo's shipped default
`.env` needs this fallback in practice, at least in this environment.

## 2. `/health` does not reflect "container is ready to receive work" the way step 1 implies

Step 1 says to gate all further action on `curl -sf http://localhost:5000/health`
returning success, before even picking a pattern or writing code. In
practice `/health` proxies Kapacitor's own ping endpoint, and the
microservice's `main.py` only starts the Kapacitor daemon if
`config.json` already exists on disk at process startup. On a fresh
container/volume (no prior `POST /config` ever applied), `config.json`
does not exist, so `/health` returns 503 indefinitely — it only becomes
200 *after* the first successful `POST /config`, which is step 4/5, not
before step 2. This isn't fatal (the REST API for uploading a package
and posting config is available well before `/health` turns green), but
following the skill literally ("wait for health before touching
anything else") would mean waiting forever on a brand-new
container/volume. Recommend either softening that instruction to "wait
for the container to accept connections" (e.g. `curl -sf .../udfs/package`
existing, or just checking the container is `Up`) or explicitly noting
that `/health` won't go green until after the first `POST /config`.

## 3. Docker Compose merge semantics for `ports:` in an override file (infra plumbing, not a skill issue per se)

Not a skill defect, but worth recording since it caused real damage in
this concurrent-eval environment: a `docker-compose.override.yml` that
only sets a new `ports:` entry does **not** replace the base file's
`ports:` list under default Compose merge behavior — it appends to it.
Since the base `docker/docker-compose.yml` in this repo hardcodes
`ports: - 5000:5000`, a plain override (as literally given in this
run's infra instructions) still leaves the container also bound to host
port 5000, which collides with any other concurrently-running instance
of this same compose project on the same host. Had to add the Compose
Spec `ports: !override` YAML tag to the override file to actually
replace (not append) the ports list. If other agents/skills generate
compose overrides expecting the base ports to be fully replaced, they
should use `!override` explicitly.

## 4. Shared `COMPOSE_PROJECT_NAME` across independent run directories

Also infra plumbing rather than a skill defect: `docker/.env`'s
`COMPOSE_PROJECT_NAME=timeseriessoftware` is identical across every
run's copy of this repo. When ~9 runs on the same host each ran
`docker compose ... up -d` concurrently, Compose reconciled against
*any* container sharing that project label regardless of which run
directory created it — it stopped and removed another run's container
during this session. Setting a unique `COMPOSE_PROJECT_NAME` per run
(in that run's own private `.env` copy) fixes this; worth calling out
explicitly in any instructions for running this skill's Docker Compose
step concurrently across isolated copies.

## Everything else matched the skill exactly

- The threshold pattern in `references/patterns.md` applied directly with
  only the field name and thresholds changed.
- `scripts/package_udf.sh` caught naming correctly (no false positives/negatives)
  and produced a valid tar on the first try.
- The deploy sequence (`POST /udfs/package` then `POST /config`) worked
  exactly as documented, including the "upload before config" ordering
  requirement.
- Flagged points appeared in `docker logs` exactly as described, with
  the UDF's `logger.info(...)` call showing up wrapped in Kapacitor's
  `"UDF log"` message.
