#
# Apache v2 license
# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

# ---------------------------------------------------------------------------
# Stage 1: kapacitor-builder - build kapacitord from source with latest Go
# ---------------------------------------------------------------------------
ARG GO_VERSION=1.23.4
FROM golang:${GO_VERSION}-bookworm AS kapacitor-builder

ARG KAPACITOR_VERSION
WORKDIR /build

# Clone full source (not sparse) since we need to compile the daemon + UDF agent
RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    git clone --depth 1 --branch v${KAPACITOR_VERSION} \
        https://github.com/influxdata/kapacitor.git /build/kapacitor

WORKDIR /build/kapacitor

# Bump the toolchain directive and tidy modules so `go build` compiles with
# the Go version installed above (not whatever go.mod originally pinned),
# picking up all upstream stdlib/runtime CVE fixes.
RUN go mod edit -go=$(go env GOVERSION | sed 's/go//') && \
    go mod tidy && \
    go mod verify

# Static build, stripped symbols, no cgo -> smaller attack surface & no libc dep issues
RUN CGO_ENABLED=0 GOOS=linux GOFLAGS="-trimpath" \
    go build -ldflags="-s -w" -o /build/out/kapacitord ./cmd/kapacitord

# Keep the Python UDF agent files (still needed at runtime)
RUN mkdir -p /build/out/udf_agent_py && \
    cp -r /build/kapacitor/udf/agent/py/. /build/out/udf_agent_py/

# ---------------------------------------------------------------------------
# Stage 2: runtime
# ---------------------------------------------------------------------------
ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim AS runtime

ARG INSTALL_DRIVER_VERSION="26.14.37833"
ENV INSTALL_DRIVER_VERSION=${INSTALL_DRIVER_VERSION}

# Full, unscoped security upgrade - picks up every patched Debian trixie
# package, not just a hardcoded subset that goes stale between scans.
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        wget intel-gpu-tools libgomp1 ca-certificates && \
    mkdir -p /etc/init.d && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app

# Copy the self-built, CVE-free kapacitord binary + Python UDF agent
COPY --from=kapacitor-builder /build/out/kapacitord /usr/bin/kapacitord
RUN chmod +x /usr/bin/kapacitord
COPY --from=kapacitor-builder /build/out/udf_agent_py /app/kapacitor_python

COPY scripts/install_gpu_drivers.sh /tmp/install_gpu_drivers.sh
RUN chmod +x /tmp/install_gpu_drivers.sh && \
    /tmp/install_gpu_drivers.sh && \
    apt-get clean && rm -rf /tmp/install_gpu_drivers.sh && rm -rf /var/lib/apt/lists/* && rm -rf /tmp/*

ARG TIMESERIES_UID
ARG TIMESERIES_USER_NAME

# Create non-root user and group in a single layer for smaller image and better caching
RUN groupadd --gid $TIMESERIES_UID $TIMESERIES_USER_NAME && \
    useradd --no-log-init --system --uid $TIMESERIES_UID --gid $TIMESERIES_UID --create-home $TIMESERIES_USER_NAME

COPY ./requirements.txt .

# Upgrade pip/setuptools/wheel first (these themselves carry CVEs when stale),
# then install pinned, patched application requirements.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip check

# Set environment variables in a single ENV instruction for better layer caching
ENV PYTHONPATH="$PYTHONPATH:/tmp/py_package:/app/kapacitor_python/"

# Adding classifier program
# Copy Python source files in a single layer for better caching
COPY ./src/classifier_startup.py ./src/opcua_alerts.py ./src/main.py /app/

COPY ./config/kapacitor*.conf /app/config/

#Copying for Core Pinning
COPY ./docker/run.sh /app/
COPY ./docker/detect-cores.sh /app/
RUN chmod +x /app/run.sh /app/detect-cores.sh

# Optionally download copyleft sources if requested
ARG COPYLEFT_SOURCES=false
RUN if [ "$COPYLEFT_SOURCES" = "true" ]; then \
        apt-get update && \
        # Get list of installed deb packages with copyleft licenses \
        sed -Ei 's/# deb-src /deb-src /' /etc/apt/sources.list && \
        apt-get update && \
        mkdir -p /copyleft_sources/deb && cd /copyleft_sources/deb && \
        echo -n $null > copyleft_package_list.txt && \
        for package in $(dpkg -l | awk '/^ii/ {print $2}' | cut -d: -f1); do \
            grep -l 'Copyleft\|GPL\|LGPL\|EPL\|MPL\|CDDL' /usr/share/doc/${package}/copyright; \
            exit_status=$?; \
            if [ $exit_status -eq 0 ]; then \
                echo $package >> copyleft_package_list.txt; \
                apt-get source -q --download-only $package; \
            fi; \
        done; \
        # Get source code for installed Python packages with copyleft licenses \
        mkdir -p /copyleft_sources/python && \
        cd /copyleft_sources/python && \
        apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev python3-dev && \
        # Download python package sources with relevant licenses \
        pip freeze | cut -d= -f1 | while read pkg; do \
            meta=$(pip show $pkg 2>/dev/null); \
            lic=$(echo "$meta" | grep -i '^License:' | grep -E 'MPL|GPL|General Public License|EPL|Eclipse Public License|CDDL|LGPL'); \
            if [ ! -z "$lic" ]; then \
                echo "Downloading source for $pkg with license: $lic"; \
                pip download --no-binary :all: $pkg || true; \
            fi; \
        done; \
        apt-get remove --purge -y gcc libffi-dev python3-dev; \
    fi

WORKDIR /app
# Remove git and clean up to reduce image size
# Clean up without breaking Intel GPU packages
RUN rm -rf /var/lib/apt/lists/* \
           /tmp/* \
           /var/tmp/* \
           /root/.cache/pip \
           /timeseries_user/.cache/pip || true


RUN chown -R $TIMESERIES_USER_NAME:$TIMESERIES_USER_NAME /app

# Switch to non-root user for security
USER $TIMESERIES_USER_NAME



# Simple healthcheck to verify container is running
HEALTHCHECK --interval=5m CMD exit 0

# Optional CPU core pinning behavior:
# - Set CORE_PINNING to control which CPU cores the service should prefer.
# - Supported values:
#     * "e-cores"  : prefer efficiency cores
#     * "p-cores"  : prefer performance cores
#     * "lp-cores" : prefer low-power cores (if available)
# - If CORE_PINNING is unset or empty, no explicit core pinning policy is applied.
# The run.sh script uses detect-cores.sh together with CORE_PINNING (if set)
# to determine and apply the appropriate core affinity at container startup.
ENTRYPOINT ["./run.sh"]
