# Contents

- [Contents](#contents)
    - [Overview of the Kapacitor](#overview-of-the-kapacitor)
        - [Introduction to the Point-Data Analytics (Time Series Data)](#introduction-to-the-point-data-analyticstime-series-data)
            - [Starting the Example](#starting-the-example)
            - [Purpose of the Telegraf](#purpose-of-the-telegraf)
            - [Purpose of the Kapacitor](#purpose-of-the-kapacitor)
            - [Custom UDFs available in the UDFs Directory](#custom-udfs-available-in-the-udf-directory)
                - [Steps to Configure the UDFs in the Kapacitor](#steps-to-configure-the-udfs-in-the-kapacitor)
            - [Time Series Python UDFs Development](#time-series-python-udfs-development)
                - [Steps to Run the Samples of Multiple UDFs in a Single Task and Multiple Tasks Using Single UDF](#steps-to-run-the-samples-of-multiple-udfs-in-a-single-task-and-multiple-tasks-using-single-udf)
        - [Steps to Independently Build and Deploy the Kapacitor Service](#steps-to-independently-build-and-deploy-the-kapacitor-service)
            - [Steps to Independently Build the Kapacitor Service](#steps-to-independently-build-the-kapacitor-service)
            - [Steps to Independently Deploy the Kapacitor Service](#steps-to-independently-deploy-the-kapacitor-service)
            - [Deploy the Kapacitor Service without the Config Manager Agent Dependency](#deploy-the-kapacitor-service-without-the-config-manager-agent-dependency)
            - [Deploy the Kapacitor Service with the Config Manager Agent Dependency](#deploy-the-kapacitor-service-with-the-config-manager-agent-dependency)
            - [Time Series Python UDFs Development](#time-series-python-udfs-development)

## Overview of the Kapacitor

### Introduction to the Point-Data Analytics(Time Series Data)

Any integral value that gets generated over time is point data.
For examples:

- Temperature at a different time in a day.
- Number of oil barrels processed per minute.

By doing the analytics over point data, the factory can have an anomaly detection mechanism where PointDataAnalytics is considered.

IEdgeInsights uses the [TICK stack](https://www.influxdata.com/time-series-platform/)
to do point data analytics.

It has temperature anomaly detection, an example for demonstrating the time-series data analytics flow.

The high-level flow of the data is:

 MQTT-temp-sensor-->Telegraf-->Influx-->Kapacitor-->Influx.

MQTT-temp-sensor simulator sends the data to the Telegraf. Telegraf sends the same data to Influx and Influx sends it to Kapacitor. Kapacitor does anomaly detection and publishes the results back to Influx.

Here, Telegraf is the TICK stack component and supports the number of input plug-ins for data ingestion.
Influx is a time-series database.
Kapacitor is an analytics engine where users can write custom analytics plug-ins (TICK scripts).


#### Starting the Example

1. To start the mqtt-temp-sensor, refer to [tools/mqtt-publisher/README.md](../tools/mqtt/README.md).

2. If System Integrator (SI) wants to use the IEdgeInsights only for point data analytics, then analyze Video use case container ia_edge_video_analytics_microservice in `../build/docker-compose.yml`

3. Starting the EII.

   To start the EII in production mode, provisioning must be done. Following are the commands to be executed after provisioning:

   ```sh
   cd build
   docker compose build
   docker compose up -d
   ```

   To start the EII in developer mode, refer to [README](../README.md#provision-Edge-insights-for-industrial).

3. To verify the output, check the output of the following commands:

   ```sh
   docker logs -f ia_influxdb
   ```

   Following is the snapshot of sample output of the ia_influxdb command.

   ```sh
   I0822 09:03:01.705940       1 pubManager.go:111] Published message: map[data:point_classifier_results,host=ia_telegraf,topic=temperature/simulated/0 temperature=19.29358085726703,ts=1566464581.6201317 1566464581621377117]
   I0822 09:03:01.927094       1 pubManager.go:111] Published message: map[data:point_classifier_results,host=ia_telegraf,topic=temperature/simulated/0 temperature=19.29358085726703,ts=1566464581.6201317 1566464581621377117]
   I0822 09:03:02.704000       1 pubManager.go:111] Published message: map[data:point_data,host=ia_telegraf,topic=temperature/simulated/0 ts=1566464582.6218634,temperature=27.353740759929877 1566464582622771952]
   ```


#### Purpose of the Telegraf

Telegraf is a data entry point for IEdgeInsights. It supports many input plugins, which is used for point data ingestion. In the previous example, the MQ Telemetry Transport (MQTT) input plugin of Telegraf is used. Following are the configurations of the plugins:

```sh
    # # Read metrics from MQTT topic(s)
    [[inputs.mqtt_consumer]]
    #   ## MQTT broker URLs to be used. The format should be scheme://host:port,
    #   ## schema can be tcp, ssl, or ws.
        servers = ["tcp://localhost:1883"]
    #
    #   ## MQTT QoS, must be 0, 1, or 2
    #   qos = 0
    #   ## Connection timeout for initial connection in seconds
    #   connection_timeout = "30s"
    #
    #   ## Topics to subscribe to
        topics = [
        "temperature/simulated/0",
        ]
        name_override = "point_data"
        data_format = "json"
    #
    #   # if true, messages that can't be delivered while the subscriber is offline
    #   # will be delivered when it comes back (such as on service restart).
    #   # NOTE: If true, client_id MUST be set
        persistent_session = false
    #   # If empty, a random client ID will be generated.
        client_id = ""
    #
    #   ## username and password to connect MQTT server.
        username = ""
        password = ""
```

In the production mode, the Telegraf configuration file is
[Telegraf/config/telegraf.conf](../Telegraf/config/Telegraf/Telegraf.conf) and in developer mode,
the Telegraf configuration file is
[Telegraf/config/telegraf_devmode.conf](../Telegraf/config/Telegraf/Telegraf_devmode.conf).

For more information on the supported input and output plugins refer to
[https://docs.influxdata.com/telegraf/v1.10/plugins/](https://docs.influxdata.com/telegraf/v1.10/plugins/)

#### Purpose of the Kapacitor

About Kapacitor and UDF

- You can write the custom anomaly detection algorithm in PYTHON. And these algorithms are called as UDF (user-defined function). These algorithms follow certain API standards for the Kapacitor to call these UDFs at run time.

- The sample Python UDF is at [py_classifier.py](udfs/py_classifier.py) and the TICKscript  is at [py_point_classifier.tick](tick_scripts/py_point_classifier.tick)

    For more details, on Kapacitor and UDF, refer to the following links:

    i)  Writing a sample UDF at [anomaly detection](https://docs.influxdata.com/kapacitor/v1.5/guides/anomaly_detection/)

    ii) UDF and kapacitor interaction [socket_udf](https://docs.influxdata.com/kapacitor/v1.5/guides/socket_udf/)

- In production mode, the Kapacitor configuration file is [Kapacitor/config/kapacitor.conf](./config/kapacitor.conf) and in developer mode, the Kapacitor configuration file is [Kapacitor/config/kapacitor_devmode.conf](./config/kapacitor_devmode.conf).

#### Custom UDFs available in the [UDF](udfs) Directory

- UNIX Socket based UDFs

    1. py_classifier.py:Filters the points based on temperature (data <20 and >25 filtered out).

    2. humidity_classifier.py:Filter the points based on humidity (data >25 filtered out).

- Process based UDFs

    1. rfc_classifier.py:Random Forest  Classification algo sample. This UDF is used for profiling udf as well.

##### Steps to Configure the UDFs in the Kapacitor

- Keep the custom UDFs in the [udfs](udfs) directory and the TICKscript in the [tick_scripts](tick_scripts) directory.

- Keep the training data set (if any) required for the custom UDFs in the [training_data_sets](training_data_sets) directory.

- For python UDFs, any external python package dependency needs to be installed. To install the python package using conda, it can be added in the [conda_requirements.txt](conda_requirements.txt) file.

###### Steps to Configure Socket based UDFs

- Modify the UDF section in the [kapacitor.conf](config/kapacitor.conf) and in the [kapacitor_devmode.conf](config/kapacitor_devmode.conf).
  Mention the custom UDF in the configuration, for example:

  ```sh
  [udf.functions.customUDF]
    socket = "/tmp/socket_file"
    timeout = "20s"
  ```

- For python based UDF, update the values of keys named "type", "name", "tick_script", "task_name", in the
  [config.json](config.json)file, for example:

  ```sh
  "task": [{
       "tick_script": "py_point_classifier.tick",
       "task_name": "py_point_classifier",
       "udfs": [{
           "type": "python",
           "name": "py_classifier"
       }]
  }]
  ```

- For TICKscript only UDF, update the values of keys named "tick_script", "task_name", in the [config.json](config.json)file, for example:

  ```sh
  "task": [{
       "tick_script": "simple_logging.tick",
       "task_name": "simple_logging"
       }]
  ```

 >**Note:**

   1. By default, py_classifier and rfc_classifier is configured.

   2. Mention the TICKscript UDF function same as configured in the Kapacitor configuration file. For example, UDF Node in the TICKscript:

      ```sh
      @py_point_classifier()
      ```

      should be same as

      ```sh
      [udf.functions.py_point_classifier]
         socket = "/tmp/socket_file"
         timeout = "20s"
      ```

   3. python based UDF should listen on the same socket file as mentioned in the the UDF section in the [kapacitor.conf](config/kapacitor.conf) and in the [kapacitor_devmode.conf](config/kapacitor_devmode.conf). For example:

      ```sh
      [udf.functions.customUDF]
        socket = "/tmp/socket_file"
        timeout = "20s"
      ```

###### Steps to Configure Process based UDFs

- For a process based UDFs, provide the correct path of the code within the container
  in the [kapacitor.conf](config/kapacitor.conf) and in the [kapacitor_devmode.conf](config/kapacitor_devmode.conf).
  By default, the files and directories will be copied into the container under the "/EII" directory. It is recommended to keep the custom UDFs in the [udfs](udfs) directory, the path of the custom UDF will be "/EII/udfs/customUDF_name" as shown in below example.
  If the UDF is kept in different path, modify the path in the args accordingly.

  The PYTHONPATH of the Kapacitor agent directory is "/EII/go/src/github.com/influxdata/kapacitor/udf/agent/py/". Following example shows how to pass:      

    ```sh
      [udf.functions.customUDF]
         prog = "python3.7"
         args = ["-u", "/EII/udfs/customUDF"]
         timeout = "60s"
         [udf.functions.customUDF.env]
            PYTHONPATH = "/go/src/github.com/influxdata/kapacitor/udf/agent/py/"
    ```

- For python based UDF, update the values of keys named "type", "name", "tick_script", "task_name", in the
  [config.json](config.json)file, for example:

  ```sh
  "task": [{
       "tick_script": "rfc_task.tick",
       "task_name": "rfc_task",
       "udfs": [{
           "type": "python",
           "name": "rfc_classifier"
       }]
  }]

  ```
- Perform the [provisioning](../README.md#provision-Edge-insights-for-industrial) and run the EII stack.

##### Steps to Run the Samples of Multiple UDFs in a Single Task and Multiple Tasks using Single UDF

Refer to the [samples/README](../Samples/README.md)


### Steps to Independently Build and Deploy the Kapacitor Service

> **Note:** For running 2 or more microservices, we recommend that users try the use case-driven approach for building and deploying as mentioned in [Generate Consolidated Files for a Subset of Edge Insights for Industrial Services](../README.md#generate-consolidated-files-for-a-subset-of-Edge-insights-for-industrial-services)


#### Steps to Independently Build the Kapacitor Service

> **Note:** When switching between independent deployment of the service with and without the configuration manager agent service dependency, one would run into issues with the `docker compose build` w.r.t the Certificates folder existence. As a workaround, run the command `sudo rm -rf Certificates` to proceed with `docker compose build`.

To independently build the Kapacitor service, complete the following steps:

1. The downloaded source code should have a directory named Kapacitor:

    ```sh
    cd IEdgeInsights/Kapacitor
    ```
2. Copy the IEdgeInsights/build/.env file using the following command in the current folder

    ```sh
    cp ../build/.env ./core_env
    ```
    > **NOTE**: Update the HOST_IP and ETCD_HOST variables in the core_env file with your system IP.

    ```sh
      # Source the env files using the following command:
      set -a && source .env && source ./core_env && set +a
    ```

3. Independently build
    ```sh
    docker compose build
    ```

#### Steps to Independently Deploy the Kapacitor Service

You can deploy the Kapacitor service in any of the following two ways:

##### Deploy the Kapacitor Service without the Config Manager Agent Dependency

Run the following commands to deploy the Kapacitor service without Configuration Manager Agent dependency:

```sh
    # Enter the Kapacitor directory
    cd IEdgeInsights/Kapacitor
```

> Copy the IEdgeInsights/build/.env file using the following command in the current folder, if not already present.
```sh
    cp ../build/.env ./core_env
```

> **Note:** Ensure that `docker ps` is clean and `docker network ls` must not have EII bridge network.

      Update core_env file for the following: 
      1. HOST_IP and ETCD_HOST variables with your system IP.
      2. `READ_CONFIG_FROM_FILE_ENV` value to `true` and `DEV_MODE` value to `true`.

      Source the core_env using the following command:
      set -a && source .env && source ./core_env && set +a

```sh
    # Run the service
    docker compose -f docker-compose.yml -f docker-compose-dev.override.yml up -d
```
> **Note:** Kapacitor container restarts automatically when its config is modified in `config.json` file.
If user is updating the config.json file using `vi or vim` editor, it is required to append the `set backupcopy=yes` in `~/.vimrc` so that the changes done on the host machine config.json gets reflected inside the container mount point.

##### Deploy the Kapacitor Service with the Config Manager Agent Dependency

Run the following commands to deploy the Kapacitor service with the Config Manager Agent dependency:

> **Note:** Ensure that the Config Manager Agent image present in the system. If not, build the Config Manager Agent locally when independently deploying the service with Config Manager Agent dependency.

```sh
    # Enter the Kapacitor directory
    cd IEdgeInsights/Kapacitor
```

> Copy the IEdgeInsights/build/.env file using the following command in the current folder, if not already present.
```sh
    cp ../build/.env ./core_env
```

> **Note:** Ensure that `docker ps` is clean and `docker network ls` doesn't have EII bridge networks.

      Update core_env file for following:
      1. HOST_IP and ETCD_HOST variables with your system IP.
      2. `READ_CONFIG_FROM_FILE_ENV` value is set to `false`.

> Copy the docker-compose.yml from IEdgeInsights/ConfigMgrAgent as docker-compose.override.yml in IEdgeInsights/Kapacitor.

```sh
    cp ../ConfigMgrAgent/docker-compose.yml docker-compose.override.yml
```

> Copy the builder.py with standalone mode changes from IEdgeInsights/build directory
```sh
    cp ../build/builder.py
```
> Run the builder.py in standalone mode, this will generate eii_config.json and update docker-compose.override.yml
```sh
    python3 builder.py -s true
```
> Building the service (This step is optional for building the service if not already done in the `Independently buildable` step above)
```sh
    docker compose build
```
> For running the service in PROD mode, run the below command:

> **NOTE**: Make sure to update `DEV_MODE` to `false` in core_env while running in PROD mode and source the core_env using the command `set -a && source .env && source ./core_env && set +a`.
```sh
    docker compose up -d
```
> For running the service in DEV mode, run the below command:

> **NOTE**: Make sure to update `DEV_MODE` to `true` in core_env while running in DEV mode and source the core_env using the command `set -a && source .env && source ./core_env && set +a`.
```sh
    docker compose -f docker-compose.yml -f docker-compose-dev.override.yml -f docker-compose.override.yml up -d
```


### Time Series Python UDFs Development

In the DEV mode (`DEV_MODE=true` in `[WORK_DIR]/IEdgeInsights/build/.env`), the Python UDFs are being volume mounted inside the Kapacitor container image that is seen in it's `docker-compose-dev.override.yml`. This gives the flexibility for the developers to update their UDFs on the host machine and see the changes being reflected in Kapacitor. This is done by just restarting the Kapactior container without the need to rebuild the Kapacitor container image.

