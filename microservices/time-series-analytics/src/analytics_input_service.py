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
import requests
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import uvicorn

log_level = os.getenv('KAPACITOR_LOGGING_LEVEL', 'INFO').upper()
logging_level = getattr(logging, log_level, logging.INFO)

# Configure logging
logging.basicConfig(
    level=logging_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger()
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "FastAPI Input server is running"}

KAPACITOR_URL = os.getenv('KAPACITOR_URL','http://localhost:9092/kapacitor/v1/write')
CONFIG_FILE = "/app/config.json"

app_cfg = {}
@app.on_event("startup")
def startup_event():
    global app_cfg
    try:
        with open (CONFIG_FILE, 'r') as file:
            app_cfg = json.load(file)
    except Exception as e:
        logger.exception("Fetching app configuration failed, Error: {}".format(e))
        os._exit(1)

class DataPoint(BaseModel):
    measurement: str
    tags: dict
    fields: dict
    timestamp: Optional[int] = None

class Config(BaseModel):
    config : dict

def json_to_line_protocol(data_point: DataPoint):

    # Construct tags part
    tags_part = ','.join([f"{key}={value}" for key, value in data_point.tags.items()])
    
    # Construct fields part
    fields_part = ','.join([f"{key}={value}" for key, value in data_point.fields.items()])
    
    # Use current time in nanoseconds if timestamp is None
    ts = data_point.timestamp or int(time.time() * 1e9)
    # Construct line protocol
    line_protocol = f"{data_point.measurement},{tags_part} {fields_part} {ts}"
    return line_protocol

@app.post("/input")
async def receive_data(data_point: DataPoint):
    """
    Receives a data point in JSON format, converts it to InfluxDB line protocol, and sends it to the Kapacitor service.

    The input JSON must include:
        - measurement (str): The measurement name.
        - tags (dict): Key-value pairs for tags (e.g., {"location": "factory1"}).
        - fields (dict): Key-value pairs for fields (e.g., {"temperature": 23.5}).
        - timestamp (int, optional): Epoch time in nanoseconds. If omitted, current time is used.

    Example request body:
    {
        "measurement": "sensor_data",
        "tags": {"location": "factory1", "device": "sensorA"},
        "fields": {"temperature": 23.5, "humidity": 60},
        "timestamp": 1718000000000000000
    }

    Args:
        data_point (DataPoint): The data point to be processed, provided in the request body.
    Returns:
        dict: A status message indicating success or failure.
    Raises:
        HTTPException: If the Kapacitor service returns an error or if any exception occurs during processing.

    responses:
        '200':
        description: Data successfully sent to the Time series Analytics microservice
        content:
            application/json:
            schema:
                type: object
                properties:
                status:
                    type: string
                    example: success
                message:
                    type: string
                    example: Data sent to Time series Analytics microservice
        '4XX':
        description: Client error (e.g., invalid input or Kapacitor error)
        content:
            application/json:
            schema:
                $ref: '#/components/schemas/HTTPValidationError'
        '500':
        description: Internal server error
        content:
            application/json:
            schema:
                type: object
                properties:
                detail:
                    type: string
    """
    try:
        # Convert JSON to line protocol
        line_protocol = json_to_line_protocol(data_point)
        logging.info(f"Received data point: {line_protocol}")
        
        url = f"{KAPACITOR_URL}/kapacitor/v1/write?db=datain&rp=autogen"
        # Send data to Kapacitor
        response = requests.post(url, data=line_protocol, headers={"Content-Type": "text/plain"})

        if response.status_code == 204:
            return {"status": "success", "message": "Data sent to Time series Analytics microservice"}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config_change")
async def config_file_change(config_data: Config):
    """
    Endpoint to handle configuration changes.
    This endpoint can be used to update the configuration of the input service.
    Updates the configuration of the input service with the provided key-value pairs.

    ---
    requestBody:
        required: true
        content:
            application/json:
                schema:
                    type: object
                    additionalProperties: true
                example:
                    {"config": {
                        "version": "2.0"
                    }
                    }
    responses:
        200:
            description: Configuration updated successfully
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            status:
                                type: string
                                example: "success"
                            message:
                                type: string
                                example: "Configuration updated successfully"
        400:
            description: Invalid input or error processing request
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            detail:
                                type: string
                                example: "Error message"
        500:
            description: Failed to write configuration to file
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            detail:
                                type: string
                                example: "Failed to write configuration to file"
    """
    try:
        # Here you can process the config_data as needed
        config_data = config_data.config
        logger.debug(f"Configuration change received: {config_data}")
        for key in config_data.keys():
            if key in app_cfg["config"]:
                logger.info(f"Updating key {key} in current configuration for value {config_data[key]}")
                app_cfg["config"][key] = config_data[key]
            elif key in app_cfg["config"]["task"]:
                logger.info(f"Updating key {key} in current configuration for value {config_data[key]}")
                app_cfg["config"]["task"][key] = config_data[key]
            else:
                logger.warning(f"Key {key} not found in current configuration, adding it.")
                app_cfg["config"][key] = config_data[key]
        try:
            with open(CONFIG_FILE, 'w') as file:
                json.dump(app_cfg, file, indent=4)
        except Exception as e:
            logger.error(f"Failed to write configuration to file: {e}")
            raise HTTPException(status_code=500, detail="Failed to write configuration to file")
        return {"status": "success", "message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
