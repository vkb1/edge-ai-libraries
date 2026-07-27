#!/usr/bin/env bash
#
# Apache v2 license
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# Package (and locally validate) a UDF deployment package for the Time
# Series Analytics microservice's POST /udfs/package endpoint, so naming
# mistakes get caught here instead of as a 400/422 from the server.
#
# Usage: package_udf.sh <udf_name> [source_dir]
#
#   <udf_name>   Must match udfs.name in config.json, the UDF node name in
#                the tick script (@<udf_name>()), and the .py/.tick filenames.
#   [source_dir] Directory containing udfs/, tick_scripts/, and optionally
#                models/. Defaults to the current directory.
#
# Produces <udf_name>.tar in the current directory, ready for:
#   curl -X POST http://localhost:5000/udfs/package -F "file=@<udf_name>.tar"

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <udf_name> [source_dir]" >&2
  exit 1
fi

UDF_NAME="$1"
SRC_DIR="${2:-.}"

UDF_PY="$SRC_DIR/udfs/${UDF_NAME}.py"
TICK_SCRIPT="$SRC_DIR/tick_scripts/${UDF_NAME}.tick"
MODEL_DIR="$SRC_DIR/models"

fail=0

if [[ ! -f "$UDF_PY" ]]; then
  echo "Missing $UDF_PY -- the server requires udfs/<name>.py named exactly '${UDF_NAME}.py'." >&2
  fail=1
fi

if [[ ! -f "$TICK_SCRIPT" ]]; then
  echo "Missing $TICK_SCRIPT -- the server requires tick_scripts/<name>.tick named exactly '${UDF_NAME}.tick'." >&2
  fail=1
fi

if [[ -f "$TICK_SCRIPT" ]] && ! grep -q "@${UDF_NAME}(" "$TICK_SCRIPT"; then
  echo "Warning: $TICK_SCRIPT does not invoke '@${UDF_NAME}()'." >&2
  echo "         config.json's udfs.name is wired straight to this node name at startup." >&2
fi

if [[ -d "$MODEL_DIR" ]] && ! find "$MODEL_DIR" -type f -name "${UDF_NAME}*" | grep -q .; then
  echo "Warning: models/ exists but has no file starting with '${UDF_NAME}'." >&2
  echo "         If config.json's udfs.models will be set, the server requires one." >&2
fi

if [[ $fail -ne 0 ]]; then
  echo "Fix the above before packaging." >&2
  exit 1
fi

tar_members=(udfs tick_scripts)
[[ -d "$MODEL_DIR" ]] && tar_members+=(models)

out_tar="${UDF_NAME}.tar"
tar cf "$out_tar" -C "$SRC_DIR" "${tar_members[@]}"

echo "Wrote $out_tar"
echo
echo "Next:"
echo "  curl -X POST http://localhost:5000/udfs/package -F \"file=@${out_tar}\""
echo "  curl -s -X POST http://localhost:5000/config -H 'Content-Type: application/json' \\"
echo "    -d '{\"udfs\": {\"name\": \"${UDF_NAME}\"}}'"
