<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Deploying a UDF: Package Format & Troubleshooting

The canonical, maintained walkthrough for the deploy curl sequence and the
full REST API already lives in this microservice's own docs — read those
rather than duplicating them here:

- [Get Started](https://github.com/open-edge-platform/edge-ai-libraries/blob/main/microservices/time-series-analytics/docs/user-guide/get-started.md) —
  the exact `docker compose up` -> package -> upload -> `POST /config` ->
  `POST /input` -> verify sequence, worked end-to-end with the built-in
  `temperature_classifier` sample.
- [Configure Microservice](https://github.com/open-edge-platform/edge-ai-libraries/blob/main/microservices/time-series-analytics/docs/user-guide/how-to-configure.md) —
  the full `config.json` shape (`udfs.name`/`.models`/`.device`,
  `alerts.mqtt`, `alerts.opcua`), field by field.
- [Access Microservice API](https://github.com/open-edge-platform/edge-ai-libraries/blob/main/microservices/time-series-analytics/docs/user-guide/how-to-access-api.md) —
  every REST route with a request/response example, including
  `POST /opcua_alerts`.

This file only covers what those docs don't: the package's internal
structure, and a troubleshooting table built from the server's actual
validation code rather than its happy-path docs.

## Deployment package format

A tar archive, **no wrapping top-level directory**:

```
udfs/
    <udf_name>.py          (required)
    requirements.txt       (optional)
tick_scripts/
    <udf_name>.tick        (required)
models/                    (optional -- only if config.json's udfs.models is set)
    <model files, named starting with <udf_name>>
```

Allowed member extensions: `.py .tick .txt .cb .pkl .json .joblib .xml .bin
.onnx .pt .pth` — anything else fails upload. The upload is also
security-scanned (path traversal, symlinks, encrypted payloads, tar-bomb
expansion) before extraction, independent of the structural check above.

Build it with [`../scripts/package_udf.sh`](../scripts/package_udf.sh)
(validates names locally before tarring) rather than a bare `tar cf` —
naming mismatches are the most common upload failure and the script catches
them immediately instead of round-tripping through a 400/422.

## Order matters

Upload the package (`POST /udfs/package`) *before* `POST /config` —
`POST /config` validates that the named package's files already exist on
disk and fails otherwise. If you change a UDF or tick script for a name
that's already active, re-upload the package, then re-apply config with
`?restart=true` to force Kapacitor to pick up the new files.

## Troubleshooting

| Symptom | Likely cause -> action |
|---|---|
| `POST /udfs/package` returns 400 | Missing/misnamed `udfs/*.py` or `tick_scripts/*.tick`, disallowed file extension, or the archive failed the security scan (path traversal/symlink/tar-bomb) — re-run `package_udf.sh` and read its warnings |
| `POST /udfs/package` returns 413 | Tar exceeds `UDF_MAX_FILE_SIZE_MB` (default 100 MB) |
| `POST /config` returns 422 "UDF deployment package validation failed for `<name>`" | Package for that name wasn't uploaded yet, `udfs.name` doesn't match the uploaded `.py`/`.tick` filenames, or a `models/<name>*` file is missing while `udfs.models` is set — check upload order above |
| `POST /config` returns 413 | `config.json` payload exceeds 5 KB |
| Task enables but no points ever reach the UDF | `.measurement('...')` in the tick script doesn't match the `topic` sent to `POST /input` — see [`tickscript-basics.md`](tickscript-basics.md) |
| `GET /health` returns 503 | Kapacitor daemon isn't running — check `docker logs -f ia-time-series-analytics-microservice` |
| UDF errors, but the container keeps running | Exec in and read the Kapacitor log directly: `docker exec -it ia-time-series-analytics-microservice bash` then `cat /tmp/log/kapacitor/kapacitor.log \| grep -i error` |
| Config or package changes don't seem to take effect | Re-apply with `?restart=true` (see "Order matters" above) |
