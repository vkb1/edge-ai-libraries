#
# Apache v2 license
# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

from kapacitor.udf.agent import Agent, Handler, Server
from kapacitor.udf import udf_pb2
import logging
import os

log_level = os.getenv('KAPACITOR_LOGGING_LEVEL', 'INFO').upper()
logging_level = getattr(logging, log_level, logging.INFO)

# Configure logging
logging.basicConfig(
    level=logging_level,  # Set the log level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log format
)

logger = logging.getLogger()

# Safe operating band for hydraulic pressure, in bar.
PRESSURE_LOW_BAR = 80
PRESSURE_HIGH_BAR = 150

# Flags hydraulic pressure readings that fall outside the safe operating band
# (below PRESSURE_LOW_BAR or above PRESSURE_HIGH_BAR) and mirrors those points
# back to Kapacitor.
class PressureGuardHandler(Handler):
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
        pressure = None
        if "pressure_bar" in point.fieldsDouble:
            pressure = point.fieldsDouble["pressure_bar"]
        elif "pressure_bar" in point.fieldsInt:
            pressure = point.fieldsInt["pressure_bar"]

        if pressure is None or isinstance(pressure, (int, float)) is False:
            logger.error(f"Invalid pressure_bar data received - {pressure}")
        else:
            logger.debug(f"Received pressure_bar point data {pressure}")
            if pressure < PRESSURE_LOW_BAR or pressure > PRESSURE_HIGH_BAR:
                response = udf_pb2.Response()
                response.point.CopyFrom(point)
                logger.info(
                    f"Pressure {pressure} bar is outside the safe operating band "
                    f"{PRESSURE_LOW_BAR}-{PRESSURE_HIGH_BAR}."
                )
                self._agent.write_response(response, True)

    def end_batch(self, end_req):
        raise Exception("not supported")

if __name__ == '__main__':
    # Create an agent
    agent = Agent()

    # Create a handler and pass it an agent so it can write points
    h = PressureGuardHandler(agent)

    # Set the handler on the agent
    agent.handler = h

    # Anything printed to STDERR from a UDF process gets captured
    # into the Kapacitor logs.
    agent.start()
    agent.wait()
