<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# TICKscript Basics for This Microservice

The tick script is what wires an incoming point stream to your UDF. Every
deployment here uses the same three lines; start from
[`../assets/tick_template.tick`](../assets/tick_template.tick) and fill in
two names.

```
dbrp "datain"."autogen"
var data0 = stream
        |from()
                .measurement('point_data')
data0
    @temperature_classifier()
```

## The two things you actually customize

1. **`.measurement('point_data')`** — must equal the `topic` field you send
   in `POST /input`'s body (`{"topic": ..., "fields": {...}}`). The
   microservice converts that JSON into InfluxDB line protocol where
   `topic` becomes the measurement name, so a mismatch here means your
   stream node silently sees zero points — nothing errors, data just never
   arrives at your UDF.
2. **`@temperature_classifier()`** — the UDF node name. Must equal
   `udfs.name` in `config.json` and the `.py`/`.tick` filenames (see
   [`udf-authoring.md`](udf-authoring.md#the-one-gotcha-to-know-first)).

`dbrp "datain"."autogen"` is fixed — `datain` is the InfluxDB database this
microservice always writes into; leave it as-is.

## Optional: scope processing with `.where()`

If `POST /input`'s `tags` carry something you want to filter on before it
reaches your UDF (e.g. a sensor ID), insert a `.where()` node between
`.measurement()` and the UDF call:

```
var data0 = stream
        |from()
                .measurement('point_data')
        |where(lambda: "sensor_id" == 'sensor-042')
data0
    @temperature_classifier()
```

## Alerting: two different mechanisms, don't conflate them

This microservice supports two separate alert paths, wired very
differently — pick based on what `config.json`'s `alerts` section the
deployment actually configures:

- **MQTT** is a *native TICKscript integration*. When `config.json`'s
  `alerts.mqtt` is set, the microservice registers that broker with the
  Kapacitor daemon itself, and you chain a Kapacitor `|alert()...mqtt(...)`
  node directly off your UDF's output in the tick script:
  ```
  data0
      @temperature_classifier()
      |alert()
          .message('Anomaly: {{ index .Fields "value" }}')
          .mqtt('my_mqtt_broker')   // must equal alerts.mqtt.name in config.json
  ```
- **OPC UA** is *not* wired through the tick script at all — it's a plain
  REST endpoint (`POST /opcua_alerts`) that reads `config.json`'s
  `alerts.opcua` to know which server/node to forward to. Nothing in this
  microservice calls that endpoint automatically based on your UDF's
  output; whatever is watching the anomaly points (your UDF via an HTTP
  call to `http://localhost:5000/opcua_alerts`, or an external consumer
  polling results) has to call it explicitly. Request shape:
  [Access Microservice API](https://github.com/open-edge-platform/edge-ai-libraries/blob/main/microservices/time-series-analytics/docs/user-guide/how-to-access-api.md).

Full config key reference for both (field-by-field, with examples):
[Configure Microservice](https://github.com/open-edge-platform/edge-ai-libraries/blob/main/microservices/time-series-analytics/docs/user-guide/how-to-configure.md).
