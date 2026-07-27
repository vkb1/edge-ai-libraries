#
# Apache v2 license
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
"""
Kapacitor stream UDF template for the Time Series Analytics microservice.

Rename this file to <udf_name>.py and put it under udfs/ in your deployment
package. <udf_name> must match "udfs.name" in config.json, the UDF node name
in the tick script (@<udf_name>()), and the tick script's own filename
(tick_scripts/<udf_name>.tick) -- the microservice wires these together by
name at startup, so a mismatch anywhere silently breaks the pipeline.

See ../references/udf-authoring.md for the full method contract, and
../references/patterns.md for ready-made point() bodies (threshold check,
rate-of-change, rolling z-score, model inference).
"""
import logging
import os

from kapacitor.udf.agent import Agent, Handler
from kapacitor.udf import udf_pb2

log_level = os.getenv('KAPACITOR_LOGGING_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger()

# Populated by the microservice when config.json's udfs.models / udfs.device
# are set -- see ../references/udf-authoring.md#model-loading.
MODEL_PATH = os.environ.get("MODEL_PATH")
DEVICE = os.environ.get("DEVICE", "auto")


class MyAnalyticsHandler(Handler):
    """Rename this class; keep the method contract Kapacitor expects."""

    def __init__(self, agent):
        self._agent = agent
        # Kapacitor keeps one UDF process alive per enabled task, not per
        # point, so instance state here (rolling windows, a previous value
        # for rate-of-change, a loaded model) persists across point() calls.
        # Example: self.model = joblib.load(MODEL_PATH) if MODEL_PATH else None

    def info(self):
        response = udf_pb2.Response()
        response.info.wants = udf_pb2.STREAM
        response.info.provides = udf_pb2.STREAM
        return response

    def init(self, init_req):
        response = udf_pb2.Response()
        response.init.success = True
        return response

    def snapshot(self):
        # Most deployments don't need cross-restart state recovery since
        # config is reapplied fresh on restart -- an empty snapshot is fine.
        response = udf_pb2.Response()
        response.snapshot.snapshot = b''
        return response

    def restore(self, restore_req):
        response = udf_pb2.Response()
        response.restore.success = False
        response.restore.error = 'not implemented'
        return response

    def begin_batch(self, begin_req):
        raise Exception("not supported")

    def point(self, point):
        # Field names here must match the "fields" keys sent to POST /input.
        value = point.fieldsDouble.get("value")
        if value is None:
            logger.error("Expected double field 'value' missing from point")
            return

        # --- replace with your analytics (see references/patterns.md) ---
        is_anomalous = False
        # ------------------------------------------------------------------

        if is_anomalous:
            response = udf_pb2.Response()
            response.point.CopyFrom(point)
            logger.info("Flagged anomalous point: value=%s", value)
            self._agent.write_response(response, True)

    def end_batch(self, end_req):
        raise Exception("not supported")


if __name__ == '__main__':
    agent = Agent()
    agent.handler = MyAnalyticsHandler(agent)
    # Anything printed to stderr from a UDF process is captured into the
    # Kapacitor logs (/tmp/log/kapacitor/kapacitor.log inside the container).
    agent.start()
    agent.wait()
