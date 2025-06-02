# Custom User Configuration

This guide provides advanced configuration instructions for the **Time Series Analytics Microservice**, including setting up custom User-Defined Functions (UDFs), integrating with a model registry, and configuring alerts.

---

## Configuring Custom UDFs

### Using Custom UDFs with Volume Mounts

To use custom UDFs with the Time Series Analytics Microservice, ensure the following directory structure is in place:

```
time_series_analytics_microservice
├── docker-compose.yml
├── config
│   ├── kapacitor_devmode.conf
│   ├── kapacitor.conf
├── udfs
│   ├── requirements.txt
│   ├── <udf_script.py>
├── tick_scripts
│   ├── <tick_script.tick>
├── models
    ├── <model_file.pkl>
```

#### Directory Details

1. **`config/`**:
   - Contains Kapacitor configuration files:
     - `kapacitor_devmode.conf`
   - Update the `udf` section in above file to include the task name and UDF script name:

     ```bash
     [udf]
     # Configuration for UDFs (User Defined Functions)
     [udf.functions]
         [udf.functions.<task_name>]
         prog = "python3"
         args = ["-u", "/app/udfs/<udf_script.py>"]
         timeout = "60s"
         [udf.functions.<task_name>.env]
             PYTHONPATH = "/app/kapacitor_python/:/tmp/py_package"
     ```

2. **`udfs/`**:
   - Contains Python scripts for UDFs.
   - If additional Python packages are required, list them in `requirements.txt` using pinned versions.

3. **`tick_scripts/`**:
   - Contains TICK scripts for data processing, analytics, and alerts.
   - Example TICK script:
     
     ```bash
     dbrp "datain"."autogen"

     var data0 = stream
         |from()
             .database('datain')
             .retentionPolicy('autogen')
             .measurement('opcua')
         @windturbine_anomaly_detector()
         |alert()
             .crit(lambda: "anomaly_status" > 0)
             .message('Anomaly detected: Wind Speed: {{ index .Fields "wind_speed" }}, Grid Active Power: {{ index .Fields "grid_active_power" }}, Anomaly Status: {{ index .Fields "anomaly_status" }}')
             .mqtt('my_mqtt_broker')
             .topic('alerts/wind_turbine')
             .qos(1)
         |log()
             .level('INFO')
         |influxDBOut()
             .buffer(0)
             .database('datain')
             .measurement('opcua')
             .retentionPolicy('autogen')
     ```
   - Key sections:
     - **Input**: Fetch data from Telegraf (stream).
     - **Processing**: Apply UDFs for analytics.
     - **Alerts**: Configuration for publishing alerts (e.g., MQTT). Refer [link](#Publishing-mqtt-alerts)
     - **Logging**: Set log levels (`INFO`, `DEBUG`, `WARN`, `ERROR`).
     - **Output**: Publish processed data.

   For more details, refer to the [Kapacitor TICK Script Documentation](https://docs.influxdata.com/kapacitor/v1/reference/tick/introduction/).

4. **`models/`**:
   - Contains model files (e.g., `.pkl`) used by UDF scripts.

---

## Fetching Models from the Model Registry

### Uploading Models to the Model Registry

1. Create a ZIP file with the following structure:
   ```
   udfs/
       ├── requirements.txt
       ├── <udf_script.py>
   tick_scripts/
       ├── <tick_script.tick>
   models/
       ├── <model_file.pkl>
   ```
2. Open the Model Registry Swagger UI at `http://<ip>:32002`.
3. Expand the `models` POST method and click **Try it out**.
4. Upload the ZIP file, specify the `name` and `version`, and click **Execute**.

### Updating `config.json` for Model Registry Integration

To fetch UDFs and models from the Model Registry, update the configuration file at:
`~/timeseries-ai-stack/sample_apps/windturbine_anomaly_detection/time_series_analytics_microservice/config.json`.

1. Set `fetch_from_model_registry` to `true`.
2. Specify the `task_name` and `version` as defined in the Model Registry.
   > **Note**: Mismatched task names or versions will cause the microservice to restart.
3. Update the `tick_script` and `udfs` sections with the appropriate `name` and `models` details.

---

## Publishing MQTT Alerts

### MQTT Configuration in Time Series Analytics Microservice

To enable MQTT alerts, add the following configuration to `kapacitor_devmode.conf`:

```bash
[[mqtt]]
  enabled = true
  name = "my_mqtt_broker"
  default = true
  url = "tcp://ia-mqtt-broker:1883"
  username = ""
  password = ""
```

> **Note**: For external MQTT brokers with TLS, mount the required certificates to `/run/secrets/mqtt_certs` and update the `ssl-ca`, `ssl-cert`, and `ssl-key` paths in the configuration.

### Sample MQTT Alert in TICK Script

```bash
@windturbine_anomaly_detector()
|alert()
    .crit(lambda: "anomaly_status" > 0)
    .message('Anomaly detected: Wind Speed: {{ index .Fields "wind_speed" }}, Grid Active Power: {{ index .Fields "grid_active_power" }}, Anomaly Status: {{ index .Fields "anomaly_status" }}')
    .mqtt('my_mqtt_broker')
    .topic('alerts/wind_turbine')
    .qos(1)
```

> **Note**: Setting **QoS** to `1` ensures messages are delivered at least once. Alerts are preserved and resent if the MQTT broker reconnects after downtime.

For more details, refer to the [Kapacitor MQTT Alert Documentation](https://docs.influxdata.com/kapacitor/v1/reference/event_handlers/mqtt/).

---

## Subscribing to MQTT Alerts

To subscribe to MQTT alerts:

### Docker compose deployment

To subscribe to all MQTT topics, execute the following command:

```sh
docker exec -ti ia-mqtt-broker mosquitto_sub -h localhost -v -t '#' -p 1883
```

To subscribe to a specific MQTT topic, such as `alerts/wind_turbine`, use the following command. Note that the topic information can be found in the TICKScript:

```sh
docker exec -ti ia-mqtt-broker mosquitto_sub -h localhost -v -t alerts/wind_turbine -p 1883
```

### Helm deployment

To subscribe to MQTT topics in a Helm deployment, execute the following command:

Identify the the MQTT broker pod name by running:
```sh
kubectl get pods -n apps | grep mqtt-broker
```

Use the pod name from the output of the above command to subscribe to all topics:
```sh
kubectl exec -it -n apps <mqtt_broker_pod_name> -- mosquitto_sub -h localhost -v -t '#' -p 1883
```

To subscribe to the `alerts/wind_turbine` topic, use the following command:

```sh
kubectl exec -it -n apps <mqtt_broker_pod_name> -- mosquitto_sub -h localhost -v -t alerts/wind_turbine -p 1883
```

> **Note:**
> If you are deploying with the Edge Orchestrator, make sure to export the `KUBECONFIG` environment variable.

---

## Publishing OPC-UA Alerts

To enable OPC-UA alerts in `Time Series Analytics Microservice`, please follow below steps.
The way to verify if the OPC-UA alerts are getting published would be check the `Time Series Analytics Microservice` logs OR
have any third-party OPC-UA client to connect to OPC-UA server to verify this.

1. Update the `config.json` file:
   ```json
   "alerts": {
       "opcua": {
           "opcua_server": "opc.tcp://ia-opcua-server:4840/freeopcua/server/",
           "namespace": 1,
           "node_id": 2004
       }
   }
   ```
2. Modify the TICK script:
   ```bash
   data0
       |alert()
           .crit(lambda: "anomaly_status" > 0)
           .message('Anomaly detected: Wind Speed: {{ index .Fields "wind_speed" }}, Grid Active Power: {{ index .Fields "grid_active_power" }}, Anomaly Status: {{ index .Fields "anomaly_status" }}')
           .noRecoveries()
           .post('http://localhost:5000/opcua_alerts')
           .timeout(30s)
   ```

> **Note**:
> - The `noRecoveries()` method suppresses recovery alerts, ensuring only critical alerts are sent.

---

## Enabling System Metrics Dashboard

To enable the system metrics dashboard for validation, run the following command:

```bash
cd ~/timeseries-ai-stack/sample_apps/windturbine_anomaly_detection
make up_opcua_ingestion INCLUDE=validation
```

> **Note**: The system metrics dashboard is only supported with Docker Compose deployments and requires `Telegraf` to run as the `root` user.