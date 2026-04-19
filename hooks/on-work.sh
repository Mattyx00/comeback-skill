#!/bin/bash
source "$(dirname "$0")/lib.sh"
read_stdin_once >/dev/null
feature_enabled youtube || exit 0
PORT=$(get_port_from_stdin)
curl -s -X POST "http://localhost:$PORT/play" >/dev/null 2>&1 || true
