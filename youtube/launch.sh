#!/bin/bash
# comeback — YouTube feature launcher.
# Requires features.youtube=true in comeback.json. Spawns the local player server
# and opens the video. Hook registration is handled by ../install.py, not here.

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

PROJECT_DIR="$PWD"
PORT=$((7000 + $(echo "$PROJECT_DIR" | cksum | awk '{print $1}') % 2000))
STATE_FILE="/tmp/comeback-youtube-${PORT}.env"
LOG_FILE="/tmp/comeback-youtube-${PORT}.log"

BOLD='\033[1m'; RESET='\033[0m'
CYAN='\033[0;36m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; RED='\033[0;31m'; DIM='\033[2m'

step() { echo -e "  ${CYAN}▸${RESET} $1"; }
ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $1"; }
fail() { echo -e "  ${RED}✗${RESET} $1"; }

URL="$1"

if [ -z "$URL" ]; then
  fail "Nessun URL fornito."
  echo -e "  ${DIM}Uso: /comeback youtube https://youtube.com/watch?v=...${RESET}"
  exit 1
fi

if [ "$URL" = "stop" ]; then
  step "Arresto YouTube (porta $PORT)..."
  if [ -f "$STATE_FILE" ]; then
    # shellcheck disable=SC1090
    source "$STATE_FILE"
    kill "$SERVER_PID" 2>/dev/null || pkill -f "server.py.*$PORT" 2>/dev/null || true
    rm -f "$STATE_FILE"
    ok "Server fermato."
  else
    warn "Nessuna sessione YouTube attiva per questo progetto."
  fi
  exit 0
fi

# Config gate: refuse to start if the youtube feature is disabled
if ! python3 "$SKILL_DIR/config.py" --feature youtube --cwd "$PROJECT_DIR"; then
  fail "Feature 'youtube' disabilitata nella config."
  echo -e "  ${DIM}Abilitala con: /comeback enable youtube${RESET}"
  exit 1
fi

echo -e "${CYAN}${BOLD}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║   🎵  comeback · youtube                ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${RESET}"

step "Verifico Python 3..."
if ! command -v python3 &>/dev/null; then
  fail "Python 3 non trovato. Installalo con: brew install python"
  exit 1
fi
ok "Python 3 trovato ($(python3 --version 2>&1))"

step "Analizzo URL..."
if echo "$URL" | grep -q "youtu.be/"; then
  VIDEO_ID=$(echo "$URL" | sed 's|.*youtu.be/||' | sed 's|[?&].*||')
elif echo "$URL" | grep -q "v="; then
  VIDEO_ID=$(echo "$URL" | sed 's|.*v=||' | sed 's|[&].*||')
else
  VIDEO_ID="$URL"
fi
ok "Video ID: ${BOLD}$VIDEO_ID${RESET}"

if curl -s "http://localhost:$PORT/state" > /dev/null 2>&1; then
  ok "Server già attivo su porta $PORT."
  SERVER_PID=$(lsof -ti tcp:$PORT 2>/dev/null | head -1)
else
  step "Avvio server su http://localhost:$PORT ..."
  python3 "$SKILL_DIR/youtube/server.py" "$VIDEO_ID" "$PORT" >> "$LOG_FILE" 2>&1 &
  SERVER_PID=$!
  for i in 1 2 3 4 5; do
    sleep 0.4
    if curl -s "http://localhost:$PORT/state" > /dev/null 2>&1; then break; fi
    if [ $i -eq 5 ]; then
      fail "Server non risponde. Controlla $LOG_FILE"
      exit 1
    fi
  done
  ok "Server avviato (PID $SERVER_PID)"
fi

step "Apro il player nel browser..."
curl -s -X POST "http://localhost:$PORT/play?lock=5" > /dev/null
open "http://localhost:$PORT/?v=$VIDEO_ID"
sleep 0.8

BROWSER=""
for b in "Google Chrome" "Arc" "Brave Browser" "Microsoft Edge" "Safari"; do
  if osascript -e "tell application \"$b\" to get URL of active tab of front window" 2>/dev/null | grep -q "localhost:$PORT"; then
    BROWSER="$b"
    break
  fi
done
ok "Browser: ${BOLD}${BROWSER:-default}${RESET}"

cat > "$STATE_FILE" <<EOF
PORT=$PORT
SERVER_PID=$SERVER_PID
BROWSER=$BROWSER
VIDEO_ID=$VIDEO_ID
PROJECT=$PROJECT_DIR
EOF

echo ""
echo -e "  ${BOLD}▶ YouTube attivo${RESET} ${DIM}(porta $PORT)${RESET}"
echo -e "  ${DIM}Il video parte mentre Claude lavora,"
echo -e "  si mette in pausa quando aspetta la tua risposta."
echo -e "  🔇 Clicca sull'indicatore nel player per attivare l'audio.${RESET}"
echo -e "  ${DIM}Per fermare: /comeback youtube stop${RESET}"
echo ""
