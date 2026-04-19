#!/bin/bash
# Stop — Claude finished its turn. Dispatch to the three comeback features.
source "$(dirname "$0")/lib.sh"
read_stdin_once >/dev/null

# 1. YouTube: pause the video + minimize its browser window (if running)
if feature_enabled youtube; then
  PORT=$(get_port_from_stdin)
  curl -s -X POST "http://localhost:$PORT/pause" >/dev/null 2>&1 || true
  YT_FILE=$(youtube_file_for_port "$PORT")
  if [ -f "$YT_FILE" ]; then
    # shellcheck disable=SC1090
    source "$YT_FILE"
    minimize_browser_tab "$BROWSER" "$PORT"
  fi
fi

# 2. Ring: play notification sound (backgrounded)
if feature_enabled ring; then
  SOUND=$(get_config_value ring.sound_file)
  VOL=$(get_config_value ring.volume)
  play_sound "$SOUND" "${VOL:-1.0}"
fi

# 3. Focus: bring caller window to foreground
if feature_enabled focus; then
  CALLER=""
  PROJECT=""
  SESSION_FILE=$(session_file_for_cwd)
  if [ -f "$SESSION_FILE" ]; then
    # shellcheck disable=SC1090
    source "$SESSION_FILE"
  fi
  MODE=$(get_config_value target.mode)
  if [ "$MODE" = "fixed" ]; then
    CALLER=$(get_config_value target.app)
    PROJECT=$(get_config_value target.project_path)
  fi
  # Small delay so minimize animation doesn't race the activate
  if feature_enabled youtube; then sleep 0.3; fi
  restore_focus "$CALLER" "$PROJECT"
fi
