# comeback

> Una Claude Code skill che ti richiama l'attenzione quando Claude si ferma o chiede un permesso.

Tre feature indipendenti, ognuna on/off separatamente:

- **focus** — porta in primo piano la finestra/terminale da cui hai lanciato Claude (come un debugger che torna in cima quando si ferma)
- **ring** — suono macOS di notifica (default `Glass.aiff`, configurabile)
- **youtube** — fa partire un video YouTube mentre Claude lavora, pausa+minimizza quando aspetta input

---

## Install

```bash
# Globale (tutti i progetti)
cp -r . ~/.claude/skills/comeback

# Oppure locale (solo progetto corrente)
cp -r . .claude/skills/comeback
```

Poi, da Claude Code:

```
/comeback
```

Al primo avvio la skill ti guida in un wizard:
1. **Quali feature attivare?** (multi-select)
2. **Dove salvare la config?** (globale `~/.claude/comeback.json` vs per-progetto `.claude/comeback.json`)
3. **Quale suono per `ring`?** (solo se abilitato)

Poi registra automaticamente gli hook in `settings.json`. Da quel momento in poi è sempre attivo — niente da lanciare a ogni sessione.

> **Requisiti:** macOS, Python 3 (preinstallato su macOS). Nessuna dipendenza pip.

---

## Usage

```
/comeback                              # stato corrente
/comeback config                       # ri-configura (wizard)
/comeback enable FEATURE               # FEATURE ∈ focus | ring | youtube
/comeback disable FEATURE
/comeback youtube <url>                # avvia video per questa sessione
/comeback youtube stop
/comeback ring test                    # prova il suono configurato
/comeback install                      # re-registra gli hook
/comeback uninstall                    # rimuovi tutto (incluse le vecchie free-time-player)
```

---

## How it works

```
SessionStart        → on-session-start.sh   → cattura l'app frontmost (terminale/IDE)
UserPromptSubmit    → on-work.sh            → YouTube play (se abilitato)
Pre/PostToolUse     → on-tool-*.sh          → YouTube play (se abilitato)
Stop                → on-stop.sh            → pause+minimize YouTube · ring · focus restore
PermissionRequest   → on-permission.sh      → stesso dispatch di Stop
StopFailure         → on-stop-failure.sh    → YouTube pause
SessionEnd          → on-session-end.sh     → chiudi tab, kill server, pulisci session file
```

Ogni hook legge la config (`comeback.json`) a ogni fire e no-op se la sua feature è `false`. Quindi puoi cambiare il comportamento al volo senza riavviare nulla.

La feature **focus** usa `osascript` per `activate` l'app, con caso speciale per VS Code (usa `open -a "Visual Studio Code" <project>` per gestire più workspace aperti).

La feature **youtube** lancia un piccolo server Python (`youtube/server.py`) su una porta derivata dal path del progetto (`7000 + cksum(cwd) % 2000`), apre un player HTML che polla `/state` ogni 600ms, e controlla play/pause via `POST /play` e `POST /pause` dagli hook.

La feature **ring** usa `afplay` in background.

---

## Config file

Schema di `~/.claude/comeback.json` (o `.claude/comeback.json`):

```json
{
  "version": 1,
  "features": {
    "focus": true,
    "ring": false,
    "youtube": false
  },
  "ring": {
    "sound_file": "/System/Library/Sounds/Glass.aiff",
    "volume": 1.0
  },
  "target": {
    "mode": "auto",
    "app": null,
    "project_path": null
  }
}
```

- `target.mode`: `"auto"` (usa l'app frontmost catturata a SessionStart) o `"fixed"` (usa `target.app`).
- Lookup: per-progetto vince *interamente* sulla globale (nessun merge).

---

## File layout

```
comeback/
├── SKILL.md               # definizione skill + istruzioni wizard
├── README.md              # questo file
├── CLAUDE.md              # note per chi sviluppa la skill
├── comeback.py               # CLI entrypoint invocato dallo slash command
├── config.py              # load/save/get/set config + gating
├── install.py             # registra/rimuove hook in settings.json
├── youtube/
│   ├── launch.sh          # avvia il player YouTube per una sessione
│   └── server.py          # HTTP server stdlib + player HTML
└── hooks/
    ├── lib.sh             # helper condivisi
    ├── on-session-start.sh
    ├── on-work.sh
    ├── on-tool-start.sh
    ├── on-tool-done.sh
    ├── on-stop.sh         # dispatcher 3-feature
    ├── on-stop-failure.sh
    ├── on-permission.sh   # dispatcher 3-feature
    └── on-session-end.sh
```

---

## Testing

```bash
# Syntax checks
for f in hooks/*.sh youtube/launch.sh; do bash -n "$f"; done
python3 -m py_compile config.py install.py comeback.py youtube/server.py

# Stato senza config (default → tutto off tranne focus)
python3 comeback.py status

# Crea config globale con solo focus
python3 comeback.py config-init --scope global
python3 comeback.py status

# Test suono
python3 comeback.py ring-test
```

---

Made with ❤️ for [Claude Code](https://claude.ai/code)
