#
# Apache v2 license
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

"""Trivial threshold UDF used to reproduce/verify the measurement/topic
mismatch bug described in debug-udf-not-starting.md.

Flags any point whose 'value' field exceeds THRESHOLD (default 50).
"""

from kapacitor.udf.agent import Agent, Handler, Server
from kapacitor.udf import udf_pb2
import logging
import os

log_level = os.getenv('KAPACITOR_LOGGING_LEVEL', 'INFO').upper()
logging_level = getattr(logging, log_level, logging.INFO)

logging.basicConfig(
    level=logging_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger()

THRESHOLD = float(os.getenv('THRESHOLD', '50'))


class ThresholdHandler(Handler):
    def __init__(self, agent):
        self._agent = agent

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
        value = None
        if "value" in point.fieldsDouble:
            value = point.fieldsDouble["value"]

        logger.info(f"threshold_demo UDF received point with value={value}")

        if value is None or isinstance(value, (int, float)) is False:
            logger.error(f"Invalid value data received - {value}")
        else:
            if value > THRESHOLD:
                response = udf_pb2.Response()
                response.point.CopyFrom(point)
                logger.info(f"FLAGGED: value {value} exceeds threshold {THRESHOLD}.")
                self._agent.write_response(response, True)

    def end_batch(self, end_req):
        raise Exception("not supported")


if __name__ == '__main__':
    agent = Agent()
    h = ThresholdHandler(agent)
    agent.handler = h
    agent.start()
    agent.wait()
