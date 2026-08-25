Deploy a pretrained anomaly-detection model for wind turbine sensor data through the Time Series Analytics microservice.

- A scikit-learn model (`windturbine_anomaly_detector.pkl`, an `IsolationForest`) is already trained and saved locally at `.github/skills/time-series-analytics-user/evals/files/windturbine_anomaly_detector.pkl`; copy that exact file into the deployment package's `models/` folder and wire it up for per-point inference rather than training or fabricating a new model.
- Use the pretrained-model pattern (references/patterns.md#pretrained-model-inference).
- Name the UDF `windturbine_anomaly_detector`; `config.json`'s `udfs.models` should reference the `.pkl` file, `udfs.device` set to `CPU`.

Validate the application using:
- The prebuilt `intel/ia-time-series-analytics-microservice` image via Docker Compose.
- The `models/windturbine_anomaly_detector.pkl` file placed in the deployment package alongside `udfs/windturbine_anomaly_detector.py` and `tick_scripts/windturbine_anomaly_detector.tick`.

Expected results:
- `package_udf.sh windturbine_anomaly_detector .` succeeds only once `models/windturbine_anomaly_detector.pkl` is present (the script warns if it's missing since `udfs.models` implies a required model file).
- The generated UDF loads the model once via `MODEL_PATH` in `__init__`, not per point, and flags points where `model.predict(...)` returns the anomaly convention (-1 for `IsolationForest`).
- `config.json` posted to `POST /config` includes `"models": "windturbine_anomaly_detector.pkl"` and `"device": "CPU"` under `udfs`.
- `POST /udfs/package` and `POST /config` both report `"status": "success"`, but that does **not** prove the model loaded — `POST /config`'s package validation only checks that the file exists on disk, and the UDF process loads it separately at task-start time. Confirm the model actually loaded by tailing the container log right after deploying (`docker logs -f ia-time-series-analytics-microservice`) and looking for the UDF's own `Model loaded from ...` line; a `Failed to load model from ...` line means the pipeline is live but silently classifying nothing.
- Feed at least one clearly out-of-distribution point (e.g. `value: 999.0` against normal readings in the tens) via `POST /input` and confirm the UDF's `Flagged anomalous point: value=999.0` log line appears — don't rely on `GET /health` (200) as proof of a working pipeline; it only reflects Kapacitor's daemon health, not this UDF's model-load state.

**Known gotcha (hit in a real run):** the fixture `.pkl` above was pickled with an older scikit-learn (`1.0.2`) than the microservice image's runtime scikit-learn (check with `docker exec <container> python3 -c "import sklearn; print(sklearn.__version__)"` — at last check, `1.6.1`). Loading it under a newer scikit-learn can fail inside the UDF process with `ValueError: node array from the pickle has an incompatible dtype: ... missing_go_to_left ...` (a `Tree` pickle-format change from scikit-learn 1.3's missing-value support). This failure is silent from the REST API's perspective — package upload, `POST /config`, and task-enable all still report success; only the UDF's own log line reveals it. If you hit this:
- Prefer retraining/re-pickling the model with the image's exact scikit-learn version (e.g. inside the running container, or a matching venv) over substituting an unrelated model or pattern — keep it an `IsolationForest` over the same feature(s) so the deployed use case still matches this prompt's intent.
- Do not silently swap in a different model type (e.g. a regressor) or a different anomaly-detection pattern to work around a load failure — that changes what was asked for. If a compatible retrain isn't possible, stop and flag the version mismatch back to the user instead of substituting.
