---
name: comeback
description: Ti riporta l'attenzione quando Claude si ferma o chiede un permesso. Tre feature indipendenti e configurabili — focus (porta la finestra di Claude in primo piano), ring (suono di notifica), youtube (video in play/pausa sincronizzato). Usa quando l'utente scrive /comeback.
argument-hint: [config | status | enable FEATURE | disable FEATURE | youtube URL | youtube stop | ring test | install | uninstall]
disable-model-invocation: true
allowed-tools: Bash(python3 *) Bash(bash *) Bash(curl *) Bash(open *) Bash(pkill *) Bash(chmod *) Bash(afplay *) Bash(osascript *)
---

# comeback

Quando Claude si ferma o chiede un permesso, comeback ti richiama l'attenzione. Tre feature indipendenti:

- **focus** — porta in primo piano la finestra/terminale da cui hai lanciato Claude
- **ring** — suona una notifica macOS (default: `Glass.aiff`, configurabile)
- **youtube** — fa partire un video YouTube mentre Claude lavora, pausa+minimizza quando aspetta input

Ogni feature si attiva/disattiva in modo indipendente via config.

---

## Flusso operativo

Leggi `$ARGUMENTS` e scegli uno dei rami qui sotto. Per ogni ramo, esegui i comandi indicati e mostra direttamente l'output all'utente senza aggiungere testo prima.

### Primo avvio (nessuna config esistente)

Prima di fare altro, verifica se esiste una config:

```bash
python3 "${CLAUDE_SKILL_DIR}/comeback.py" config-exists
```

Se il comando esce con codice diverso da 0 (nessuna config trovata) **e** `$ARGUMENTS` è vuoto o `"config"`, esegui il **wizard conversazionale**:

1. **Chiedi all'utente (usa AskUserQuestion)**:
   - *"Quali feature vuoi attivare?"* — multiSelect su `focus`, `ring`, `youtube`. Consiglia di lasciare `focus` attivo.
   - *"Dove vuoi salvare la configurazione?"* — single-select: `Globale (~/.claude/comeback.json)` vs `Per-progetto (.claude/comeback.json)`.
   - Se l'utente ha selezionato `ring`, chiedi: *"Quale suono preferisci?"* — opzioni: `Glass (default)`, `Ping`, `Funk`, `Submarine`, `Altro (specifica path)`. Path reale dei suoni: `/System/Library/Sounds/<Nome>.aiff`.

2. **Scrivi la config** con chiamate sequenziali (scope = scelta dell'utente, `global` o `local`):
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/comeback.py" config-init --scope <scope>
   python3 "${CLAUDE_SKILL_DIR}/comeback.py" config-set features.focus=<true|false> --scope <scope>
   python3 "${CLAUDE_SKILL_DIR}/comeback.py" config-set features.ring=<true|false> --scope <scope>
   python3 "${CLAUDE_SKILL_DIR}/comeback.py" config-set features.youtube=<true|false> --scope <scope>
   # solo se ring=true e suono custom:
   python3 "${CLAUDE_SKILL_DIR}/comeback.py" config-set ring.sound_file=<path> --scope <scope>
   ```

3. **Registra gli hook**:
   ```bash
   chmod +x "${CLAUDE_SKILL_DIR}/hooks/"*.sh
   python3 "${CLAUDE_SKILL_DIR}/install.py" --scope <scope>
   ```

4. **Mostra stato finale**:
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/comeback.py" status
   ```

5. Chiudi con:
   > ✓ **comeback configurato.** Al prossimo Stop / PermissionRequest le feature attive entreranno in azione.

### `/comeback` senza argomenti (config già esistente)

Mostra solo lo stato:
```bash
python3 "${CLAUDE_SKILL_DIR}/comeback.py" status
```

### `/comeback status`

Come sopra.

### `/comeback config`

Forza una nuova esecuzione del wizard (sovrascrive la config esistente). Stesso flusso del primo avvio.

### `/comeback enable FEATURE` / `/comeback disable FEATURE`

FEATURE ∈ `focus` | `ring` | `youtube`. Esegui:
```bash
python3 "${CLAUDE_SKILL_DIR}/comeback.py" <enable|disable> <feature> --scope <scope-corrente>
```
Se la config è per-progetto, usa `--scope local`; se globale, `--scope global`. Determina lo scope leggendo il campo `source` di `comeback.py status`.

### `/comeback youtube URL`

```bash
python3 "${CLAUDE_SKILL_DIR}/comeback.py" youtube "$URL"
```

### `/comeback youtube stop`

```bash
python3 "${CLAUDE_SKILL_DIR}/comeback.py" youtube-stop
```

### `/comeback ring test`

```bash
python3 "${CLAUDE_SKILL_DIR}/comeback.py" ring-test
```

### `/comeback install`

Registra (o ri-registra) gli hook:
```bash
python3 "${CLAUDE_SKILL_DIR}/install.py"
```

### `/comeback uninstall`

Rimuove gli hook. Chiedi prima conferma, poi:
```bash
python3 "${CLAUDE_SKILL_DIR}/install.py" --uninstall --legacy
```
(`--legacy` pulisce anche eventuali hook rimasti dalla vecchia skill `free-time-player`.)

---

## Note tecniche

- Solo macOS (`osascript`, `afplay`, `open -a`).
- Python 3 stdlib (nessun pip).
- Config: `~/.claude/comeback.json` (globale) o `.claude/comeback.json` (per-progetto, ha precedenza piena).
- Log: `/tmp/comeback.log`.
- Gli hook sono sempre registrati ma si auto-gate leggendo la config a ogni fire: se una feature è off, il suo codice non gira.
