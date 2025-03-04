# Copyright Intel Corporation

# Use the Kapacitor 1.7.6 image as the base image
ARG KAPACITOR_VERSION
FROM kapacitor:$KAPACITOR_VERSION

# Install Python and other necessary packages
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /app/kapacitor-${KAPACITOR_VERSION} && \
    git clone --single-branch -b v${KAPACITOR_VERSION} \
    https://github.com/influxdata/kapacitor.git /app/kapacitor-${KAPACITOR_VERSION} && \
    mv /app/kapacitor-${KAPACITOR_VERSION}/udf/agent/py /app/kapacitor_python && \
    rm -r kapacitor-${KAPACITOR_VERSION}

ARG TIMESERIES_UID
ARG TIMESERIES_USER_NAME
ARG PYTHON_VERSION
RUN groupadd $TIMESERIES_USER_NAME -g $TIMESERIES_UID && \
    useradd -r -u $TIMESERIES_UID -g $TIMESERIES_USER_NAME $TIMESERIES_USER_NAME

COPY requirements.txt .
COPY intel_distribution_requirements.txt .

RUN /bin/bash -c "python3 -m venv idp && \
    source idp/bin/activate && \
    pip install -i https://software.repos.intel.com/python/pypi -r intel_distribution_requirements.txt && \
    pip3 install -r requirements.txt"

ENV PYTHONPATH $PYTHONPATH:/tmp/py_package:/app/kapacitor_python/

# Adding classifier program
COPY ./udfs/ /app/udfs/
COPY classifier_startup.py /app
COPY config.json /app
# Add tick scripts and configs
COPY ./tick_scripts/* /app/tick_scripts/
COPY ./config/kapacitor*.conf /app/config/

RUN apt-get remove --purge -y git

USER $TIMESERIES_USER_NAME

HEALTHCHECK NONE

CMD ["/bin/bash", "-c", "source /app/idp/bin/activate && python3 ./classifier_startup.py"]
