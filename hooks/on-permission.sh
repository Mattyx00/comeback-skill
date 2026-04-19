#!/bin/bash
# PermissionRequest — Claude is asking user approval. Same dispatch as Stop.
source "$(dirname "$0")/lib.sh"
read_stdin_once >/dev/null

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

if feature_enabled ring; then
  SOUND=$(get_config_value ring.sound_file)
  VOL=$(get_config_value ring.volume)
  play_sound "$SOUND" "${VOL:-1.0}"
fi

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
  if feature_enabled youtube; then sleep 0.2; fi
  restore_focus "$CALLER" "$PROJECT"
fi
