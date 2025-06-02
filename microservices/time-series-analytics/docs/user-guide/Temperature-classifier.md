# Temperature Classifier

The temperature classifier udf filters the points based on temperature (data <20 and >25 filtered out)

## How it works

The flow remains same as that explained in the [Overview](./Overview.md).
Let's specifically talk about the Temperature Classifier use case here:

- **Data Processing**: **Time Series Analytics Microservice** uses the User Defined Function(UDF) deployment package(TICK Scripts, UDFs, Models) which is already built-in to the container image. The UDF deployment package is available
at `~/timeseries-ai-stack/microservices/time-series-analytics`. Directory details is as below:
  
   1. **`config.json`**:
      The `task` section defines the settings for the Kapacitor task and User-Defined Functions (UDFs).

      | Key                     | Description                                                                                     | Example Value                          |
      |-------------------------|-------------------------------------------------------------------------------------------------|----------------------------------------|
      | `fetch_from_model_registry` | Boolean flag to enable fetching UDFs and models from the Model Registry.                     | `true` or `false`                      |
      | `version`               | Specifies the version of the task or model to use.                                             | `"1.0"`                                |
      | `tick_script`           | The name of the TICK script file used for data processing and analytics.                        | `"temperature_classifier.tick"`  |
      | `task_name`             | The name of the Kapacitor task.                                                                | `"temperature_classifier"`       |
      | `udfs`                  | Configuration for the User-Defined Functions (UDFs).                                           | See below for details.                 |

      **UDFs Configuration**:

      The `udfs` section specifies the details of the UDFs used in the task.

      | Key     | Description                                                                 | Example Value                          |
      |---------|-----------------------------------------------------------------------------|----------------------------------------|
      | `type`  | The type of UDF. Currently, only `python` is supported.                     | `"python"`                             |
      | `name`  | The name of the UDF script.                                                 | `"temperature_classifier"`       |
    

      ---

      **Alerts Configuration**:

      The `alerts` section defines the settings for alerting mechanisms, such as MQTT.
      For OPC-UA configuration, please refer [Publishing OPC-UA alerts](./Custom-User-Configuration.md#publishing-opc-ua-alerts)

      **MQTT Configuration**:

      The `mqtt` section specifies the MQTT broker details for sending alerts.

      | Key                 | Description                                                                 | Example Value          |
      |---------------------|-----------------------------------------------------------------------------|------------------------|
      | `mqtt_broker_host`  | The hostname or IP address of the MQTT broker.                              | `"ia-mqtt-broker"`     |
      | `mqtt_broker_port`  | The port number of the MQTT broker.                                         | `1883`                |
      | `name`              | The name of the MQTT broker configuration.                                 | `"my_mqtt_broker"`     |


   2. **`config/`**:
      - `kapacitor_devmode.conf` would be updated as per the above `config.json` at runtime for usage.

   3. **`udfs/`**:
      - Contains the python script to process the incoming data.

   4. **`tick_scripts/`**:
      - The TICKScript `temperature_classifier.tick` determines processing of the input data coming in.
        Mainly, has the details on execution of the UDF file, storage of processed data and publishing of alerts. 


## Prerequisites

### System Requirements

| Component           | Specification                                                                                   |
|---------------------|-------------------------------------------------------------------------------------------------|
| **Processor**       | 11th Gen Intel® Core™ or Intel® Xeon® processor with Intel® HD Graphics                         |
| **RAM**             | Minimum 16 GB                                                                                   |
| **Storage**         | Minimum 64 GB (128 GB recommended)                                                              |
| **Operating System**| Ubuntu 24.04                                                                                    |
| **Docker**          | Version 24.0.72 or later                                                                        |

### Docker Installation and Configuration

1. **Install Docker**: Follow the [Docker installation guide](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository).
2. **Run Docker as Non-Root**: Follow the steps in [Manage Docker as a non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user).
3. **Configure Proxy (if required)**:
   - Set up proxy settings for Docker client and containers as described in [Docker Proxy Configuration](https://docs.docker.com/network/proxy/).
   - Example `~/.docker/config.json`:
     ```json
     {
       "proxies": {
         "default": {
           "httpProxy": "http://<proxy_server>:<proxy_port>",
           "httpsProxy": "http://<proxy_server>:<proxy_port>",
           "noProxy": "127.0.0.1,localhost"
         }
       }
     }
     ```
   - Configure the Docker daemon proxy as per [Systemd Unit File](https://docs.docker.com/engine/daemon/proxy/#systemd-unit-file).
4. **Enable Log Rotation**:
   - Add the following configuration to `/etc/docker/daemon.json`:
     ```json
     {
       "log-driver": "json-file",
       "log-opts": {
         "max-size": "10m",
         "max-file": "5"
       }
     }
     ```
   - Reload and restart Docker:
     ```bash
     sudo systemctl daemon-reload
     sudo systemctl restart docker
     ```

---

## Setup Instructions

### Clone the Repository

Clone the repository with submodules:

```bash
git clone --recurse-submodules https://github.com/intel-innersource/frameworks.ai.ai-suite-for-timeseries ~/timeseries-ai-stack
cd ~/timeseries-ai-stack
```

### Build Docker Images

Navigate to the application directory and build the Docker images:

```bash
cd ~/time-series-ai-stack/microservices/time-series-analytics/docker
docker compose build
```

### Push Docker Images (Optional)

To push images to a Docker registry:

1. Update the following fields in `~/time-series-ai-stack/microservices/time-series-analytics/docker/.env`:
   - `DOCKER_REGISTRY`
   - `DOCKER_USERNAME`
   - `DOCKER_PASSWORD`

2. Push the images:
   ```bash
   docker login $DOCKER_REGISTRY
   docker compose push
   ```

---

## Deployment Options

### Deploy with Docker Compose (Single Node)

Navigate to the application directory and run the Docker container:

```bash
cd ~/time-series-ai-stack/microservices/time-series-analytics/docker
docker compose up -d
```

> **Note:** The `kapacitor_devmode.conf` files would be auto-updated to run the configured tasks and udfs from the Time Series Analytics microservice `~/timeseries-ai-stack/microservice/time-series-analytics/config.json`.



### Verify the Temperature Classifier Results

Run below commands to see the results in time-series-analytics-microservice:


``` bash
docker logs -f ia-time-series-analytics-microservice
```

### Deploy with Helm (Kubernetes single node cluster)

#### Prerequisites

- Kubernetes cluster (v1.30.2) installed using `kubeadm`, `kubectl`, and `kubelet`.
- Helm installed ([Helm Installation Guide](https://helm.sh/docs/intro/install/)).

#### Deployment Steps

1. Generate Helm charts:
   
   - Using pre-built helm charts:
   
     ```bash
     helm pull oci://amr-registry.caas.intel.com/edge-insights/timeseries/wind-turbine-anomaly-detection-sample-app --version 1.0.0
     tar -xvzf wind-turbine-anomaly-detection-sample-app-1.0.0.tgz
     cd wind-turbine-anomaly-detection-sample-app-1.0.0
     ```

3. Install Helm charts - use only one of the options below:

      > **Note:**
      > 1. Please uninstall the helm charts if already installed.
      > 2. If the worker nodes are running behind proxy server, then please additionally set `HTTP_PROXY` and `HTTPS_PROXY` env in `<repo>/microservices/time-series-analytics/helm/values.yaml`.


    ```bash
    helm install time-series-analytics . -n apps --create-namespace
    ```

4. Verify pods and services:
   ```bash
   kubectl get pods -n apps
   kubectl get svc -n apps
   ```

7. Uninstall Helm release:
   ```bash
   helm uninstall time-series-analytics -n apps
   ```

## Troubleshooting

- Check container logs in docker compose deployment:

  ```bash
  docker logs -f <container_name>
  docker logs -f <container_name> | grep -i error
  ```
- Check pod logs in helm deployment:

  ```bash
  kubectl logs -f <pod_name>
  kubectl logs -f <pod_name> | grep -i error
  ```

## Summary

This guide demonstrated how to deploy and use the default Temperature Classifier UDF. For more details, refer to the [Overview](./Overview.md).
