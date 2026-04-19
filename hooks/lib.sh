#!/bin/bash
# Shared helpers for comeback hooks.
# Computes paths, reads config, and exposes focus/minimize primitives.

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── stdin cache ───────────────────────────────────────────────────────────────
# Hook stdin is a single-read JSON payload. Cache it so multiple helpers can
# read the same fields without racing for stdin.
COMEBACK_STDIN=""
read_stdin_once() {
  if [ -z "$COMEBACK_STDIN" ]; then
    COMEBACK_STDIN=$(cat - 2>/dev/null)
  fi
  echo "$COMEBACK_STDIN"
}

_json_field() {
  local field="$1"
  read_stdin_once | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    v = d.get('$field', '')
    print(v if v is not None else '')
except Exception:
    print('')
" 2>/dev/null
}

get_cwd()        { _json_field cwd; }
get_session_id() { _json_field session_id; }
get_reason()     { _json_field reason; }

# ── Port derivation (YouTube) ────────────────────────────────────────────────
_cwd_hash() {
  local cwd="$1"
  [ -z "$cwd" ] && { echo "0"; return; }
  echo "$cwd" | cksum | awk '{print $1}'
}

get_port_from_stdin() {
  local cwd port
  cwd=$(get_cwd)
  if [ -n "$cwd" ]; then
    port=$((7000 + $(_cwd_hash "$cwd") % 2000))
    echo "$port"
    return
  fi
  # Fallback: any active youtube state file
  local state
  state=$(ls /tmp/comeback-youtube-*.env 2>/dev/null | head -1)
  if [ -n "$state" ]; then
    grep '^PORT=' "$state" | cut -d= -f2
    return
  fi
  echo "7777"
}

# ── Session + youtube state files ─────────────────────────────────────────────
session_file_for_cwd() {
  local cwd="${1:-$(get_cwd)}"
  local h
  h=$(_cwd_hash "$cwd")
  echo "/tmp/comeback-session-${h}.env"
}

youtube_file_for_port() {
  echo "/tmp/comeback-youtube-${1}.env"
}

# ── Config gating ─────────────────────────────────────────────────────────────
feature_enabled() {
  local name="$1"
  local cwd
  cwd=$(get_cwd)
  python3 "$SKILL_DIR/config.py" --feature "$name" --cwd "$cwd"
}

get_config_value() {
  local key="$1"
  local cwd
  cwd=$(get_cwd)
  python3 "$SKILL_DIR/config.py" --get "$key" --cwd "$cwd"
}

# ── Window primitives ─────────────────────────────────────────────────────────
# Minimize the window of $BROWSER whose active tab points at localhost:$PORT.
minimize_browser_tab() {
  local browser="$1" port="$2"
  [ -z "$browser" ] && return 0
  osascript 2>/dev/null <<EOF
tell application "$browser"
  repeat with w in windows
    try
      if URL of active tab of w contains "localhost:$port" then
        set miniaturized of w to true
      end if
    end try
  end repeat
end tell
EOF
}

# Restore focus to $caller. VS Code special-case uses `open -a` with the
# project path because `activate` alone often focuses the wrong window when
# multiple VS Code workspaces are open.
restore_focus() {
  local caller="$1" project="$2"
  [ -z "$caller" ] && return 0
  if [ "$caller" = "Code" ] && [ -n "$project" ]; then
    open -a "Visual Studio Code" "$project" 2>/dev/null || true
  else
    osascript -e "tell application \"$caller\" to activate" 2>/dev/null || true
  fi
}

# Play a sound in the background. Safe if file missing or afplay absent.
play_sound() {
  local file="$1" vol="${2:-1.0}"
  [ -z "$file" ] && return 0
  [ ! -f "$file" ] && return 0
  command -v afplay >/dev/null 2>&1 || return 0
  (afplay -v "$vol" "$file" >/dev/null 2>&1 &) 2>/dev/null
}
