# Time Series Analytics Microservice

The **Time Series Analytics Microservice** handles the time series data that supports data processing.

The Time Series Analytics microservice which uses Kapacitor as the real-time data processing engine and accelerates the Machine Learning algorithms via Intel® Extension for Scikit-learn*.
More details on the Intel® Extension for Scikit-learn* at <https://www.intel.com/content/www/us/en/developer/articles/technical/easy-introduction-to-scikit-learn.html>


## Overview

The stack is built on the **TICK Stack** (Telegraf, InfluxDB, Chronograf, Kapacitor) and includes the following components running as individual containers:

- **Time Series Analytics Microservice**: Use Kapacitor to process and analyzes time series data.

The stack is designed for flexibility, scalability, and ease of integration with custom logic, making it ideal for anomaly detection, predictive maintenance, and other time series analytics use cases.

- **Programming Language**: Python

---

## High-Level Architecture

![Time Series AI Stack Architecture Diagram](./_images/time-series-ai-stack-architecture.png)

### Key Features

- Offers a complete pipeline for data ingestion, storage, processing, and visualization.
- Fully customizable to enable or disable specific services/containers (e.g., **InfluxDB** can be excluded if data storage is not required).
- Supports integration with alternative time series databases, allowing flexibility beyond **InfluxDB**.
- Extensible **Time Series Analytics Microservice** capable of running Deep Learning models by updating its container image, in addition to Machine Learning models accelerated by Intel® Extension for Scikit-learn*.
- Enables users to ingest their own data via **Telegraf** and implement custom User-Defined Functions (UDFs) in the **Time Series Analytics Microservice** to address specific time series use cases.


### Architecture Flow Summary

1. Ingest data via the inbuilt **OPC-UA** server or **MQTT** publisher to simulate the data ingestion.
2. **Telegraf** collects data from various sources using input plugins and sends it to **InfluxDB** and
   **Time Series Analytics Microservice**.
3. **InfluxDB** stores the ingested and processed data and makes it available for querying.
4. **Time Series Analytics Microservice** processes the stream data coming from **Telegraf** using custom UDFs and stores the results back in **InfluxDB**. If one wants to configure updated UDF deployment package, the **Time Series Analytics Microservice** can be configured to read the same from `Model Registry` microservice. `Model Registry` microservice helps in managing the life cycle of the machine learning models. It provides REST APIs for user to upload the UDF deployment package, more details on configuring `Model Registry` is available at [Custom User Configuration](Custom-User-Configuration.md#configuring-to-fetch-model-from-model-registry).
5. **Grafana/Gradio app** visualizes the processed data, enabling users to monitor and analyze it through interactive dashboards.

The architecture consists of four key stages: **Data Ingestion**, **Data Storage**, **Data Processing**, and **Data Visualization**. Each stage is powered by a specific component of the stack, as described below.

---

## How It Works

### 1. **Data Ingestion**

**Telegraf** is a plugin-driven server agent that collects and reports metrics from various sources. It uses input plugins to ingest data and sends it to **InfluxDB** for storage.

- **Supported Input Plugins**: The stack supports multiple input plugins. We have primarily tested the **OPC-UA** and **MQTT** plugins with our **OPC-UA** server and **MQTT** Publisher containers respectively.
- **Documentation**: Refer to the [Telegraf Documentation](https://docs.influxdata.com/telegraf/v1/) for more details.

---

### 2. **Data Storage**

**InfluxDB** is a high-performance time series database designed to handle large volumes of write and query operations. It stores both raw ingested data and processed data, which can be organized into different measurements (tables).

- **Key Features**:
  - Optimized for time series data.
  - Supports high write throughput and efficient querying.
- **Documentation**: Refer to the [InfluxDB Documentation](https://docs.influxdata.com/influxdb/v1/) for more details.

---

### 3. **Data Processing**

**Time Series Analytics Microservice** uses **Kapacitor** - a real-time data processing engine that enables users to analyze time series data. It supports both streaming and batch processing and integrates seamlessly with **InfluxDB**.
Time Series Analytics Microservice has the Intel® Extension for Scikit-learn* python package which when used in the User Defined Functions (UDFs) of Kapacitor would improve the performance of the Machine Learning algorithms.

- **Custom Logic with UDFs**:
  - Users can write custom processing logic, known as **User-Defined Functions (UDFs)**, in Python.
  - UDFs follow specific API standards, allowing **Kapacitor** to call them at runtime.
  - Processed data is stored back in **InfluxDB** by default.
- **Use Case**: Detect anomalies, trigger alerts, and perform advanced analytics.
- **Documentation**: Refer to the [Kapacitor Anomaly Detection Guide](https://docs.influxdata.com/kapacitor/v1/guides/anomaly_detection/) for details on writing UDFs.

The Time Series Analytics microservice allows customization by reading the UDF deployment package consisting of the UDF scripts, models and TICK scripts from the
Model Registry microservice.

---

### 4. **Data Visualization**

**Grafana** provides an intuitive user interface for visualizing time series data stored in **InfluxDB**. It allows users to create custom dashboards and monitor key metrics in real time.

- **Key Features**:
  - Connects seamlessly with **InfluxDB**.
  - Supports advanced visualization options.
- **Documentation**:
  - [Getting Started with Grafana and InfluxDB](https://grafana.com/docs/grafana/latest/getting-started/get-started-grafana-influxdb/)
  - [Grafana Documentation](https://grafana.com/docs/grafana/latest/)


Additionally, we have a simple web application built on the gradio python package to provide
a quick preview of the visualization.

## Learn More

- Get started with the [Wind Turbine Anomaly Detection Sample App](./Wind-Turbine-Anomaly-Detection.md).