#
# Apache v2 license
# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
from asyncua.sync import Client
import os
import logging
import time
import sys

import json
from fastapi import FastAPI, HTTPException, Request

CONFIG_FILE = "/app/config.json"

log_level = os.getenv('KAPACITOR_LOGGING_LEVEL', 'INFO').upper()

logging_level = getattr(logging, log_level, logging.INFO)

# Configure logging
logging.basicConfig(
    level=logging_level,  # Set the log level to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log format
)

logger = logging.getLogger()

app = FastAPI()

# Get the namespace and node_id from config.json file
try:
    with open (CONFIG_FILE, 'r') as file:
        app_cfg = json.load(file)

    alerts = app_cfg["config"]["alerts"]
    node_id = alerts["opcua"]["node_id"]
    namespace = alerts["opcua"]["namespace"]
    opcua_server = alerts["opcua"]["opcua_server"]
except Exception as e:
    logger.exception("Fetching app configuration failed, Error: {}".format(e))

client = Client(opcua_server)
client.application_uri = "urn:opcua:python:server"

secure_mode = os.getenv("SECURE_MODE", "false")


async def send_alert_to_opcua_async(alert_message):
    try:
        alert_node = client.get_node("ns=" + str(namespace) + ";i=" + str(node_id))
        alert_node.write_value(alert_message)
        logger.debug("Alert sent to OPC UA server: {}".format(alert_message))
    except Exception as e:
        logger.exception(e)

app = FastAPI()

@app.post("/opcua_alerts")
async def receive_alert(request: Request):
    try:
        # Parse the incoming JSON payload
        alert_data = await request.json()
        alert_message = alert_data.get('message', '')
        try:
            await send_alert_to_opcua_async(alert_message)
        except Exception as e:
            logger.exception(e)
        # Return a success response
        return {"status_code": 200,"status": "success", "message": "Alert received"}
    except Exception as e:
        # Handle any errors that occur
        raise HTTPException(status_code=400, detail=str(e))

# Optionally, add a root endpoint for testing
@app.get("/")
def read_root():
    return {"message": "FastAPI server is running"}
 
attempt = 0
max_retries = 10
while attempt < max_retries:
    try:
        if secure_mode.lower() == "true":
            kapacitor_cert = "/run/secrets/time_series_analytics_microservice_Server_server_certificate.pem"
            kapacitor_key = "/run/secrets/time_series_analytics_microservice_Server_server_key.pem"
            client.set_security_string(f"Basic256Sha256,SignAndEncrypt,{kapacitor_cert},{kapacitor_key}")
            client.set_user("admin")
        logger.info(f"Attempting to connect to OPC UA server: {opcua_server} (Attempt {attempt + 1})")
        client.connect()
        logger.info(f"Connected to OPC UA server: {opcua_server} successfully.")
        break
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        attempt += 1
        if attempt < max_retries:
            logger.info(f"Retrying in 15 seconds...")
            time.sleep(max_retries)
        else:
            logger.error(f"Max retries reached. Could not connect to the OPC UA server: {opcua_server}.")
            sys.exit(1)