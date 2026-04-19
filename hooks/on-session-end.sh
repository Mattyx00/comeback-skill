#!/bin/bash
# SessionEnd — clean up YouTube (if active) and always remove the session file.
source "$(dirname "$0")/lib.sh"
read_stdin_once >/dev/null

# /clear keeps Claude alive in the same host — don't tear down the YouTube server
REASON=$(get_reason)
if [ "$REASON" = "clear" ]; then
  exit 0
fi

# YouTube cleanup: close the player tab and kill the server
if feature_enabled youtube; then
  PORT=$(get_port_from_stdin)
  YT_FILE=$(youtube_file_for_port "$PORT")
  if [ -f "$YT_FILE" ]; then
    # shellcheck disable=SC1090
    source "$YT_FILE"
    if [ -n "$BROWSER" ]; then
      osascript 2>/dev/null <<EOF
tell application "$BROWSER"
  repeat with w in windows
    set tabsToClose to {}
    repeat with t in tabs of w
      if URL of t contains "localhost:$PORT" then
        set end of tabsToClose to t
      end if
    end repeat
    repeat with t in tabsToClose
      close t
    end repeat
  end repeat
end tell
EOF
    fi
    kill "$SERVER_PID" 2>/dev/null || pkill -f "server.py.*$PORT" 2>/dev/null || true
    rm -f "$YT_FILE"
  fi
fi

# Session (focus context) file — always cleared on real session end
SESSION_FILE=$(session_file_for_cwd)
rm -f "$SESSION_FILE"
