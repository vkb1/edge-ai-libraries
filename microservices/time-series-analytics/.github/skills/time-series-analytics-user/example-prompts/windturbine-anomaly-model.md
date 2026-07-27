Deploy a pretrained anomaly-detection model for wind turbine sensor data through the Time Series Analytics microservice.

- A scikit-learn model (`windturbine_anomaly_detector.pkl`, an `IsolationForest`) is already trained and saved locally; wire it up for per-point inference rather than writing new detection logic.
- Use the pretrained-model pattern (references/patterns.md#pretrained-model-inference).
- Name the UDF `windturbine_anomaly_detector`; `config.json`'s `udfs.models` should reference the `.pkl` file, `udfs.device` set to `CPU`.

Validate the application using:
- The prebuilt `intel/ia-time-series-analytics-microservice` image via Docker Compose.
- The `models/windturbine_anomaly_detector.pkl` file placed in the deployment package alongside `udfs/windturbine_anomaly_detector.py` and `tick_scripts/windturbine_anomaly_detector.tick`.

Expected results:
- `package_udf.sh windturbine_anomaly_detector .` succeeds only once `models/windturbine_anomaly_detector.pkl` is present (the script warns if it's missing since `udfs.models` implies a required model file).
- The generated UDF loads the model once via `MODEL_PATH` in `__init__`, not per point, and flags points where `model.predict(...)` returns the anomaly convention (-1 for `IsolationForest`).
- `config.json` posted to `POST /config` includes `"models": "windturbine_anomaly_detector.pkl"` and `"device": "CPU"` under `udfs`.
