#!/bin/bash
# SessionStart — capture the frontmost app (host terminal/IDE) so that the
# `focus` feature can restore focus there on Stop / PermissionRequest.
# Runs unconditionally: it's the data source the focus feature depends on.
source "$(dirname "$0")/lib.sh"
read_stdin_once >/dev/null

CWD=$(get_cwd)
[ -z "$CWD" ] && exit 0

SESSION_FILE=$(session_file_for_cwd "$CWD")
CALLER=$(osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true' 2>/dev/null)
SESSION_ID=$(get_session_id)

cat > "$SESSION_FILE" <<EOF
CALLER=$CALLER
PROJECT=$CWD
SESSION_ID=$SESSION_ID
STARTED_AT=$(date +%s)
EOF
