#!/usr/bin/env python3
"""comeback — slash-command entrypoint.

Thin dispatcher. Heavy logic lives in config.py (state), install.py (hooks),
and youtube/launch.sh (player).

Subcommands:
  status                                 current config + session context
  config-exists                          exit 0 if any config present, 1 otherwise
  config-init   [--scope global|local]   create default config (no overwrite)
  config-set    key=value [--scope …]    write a single value
  enable        <feature>                set features.<name>=true (feature ∈ focus|ring|youtube)
  disable       <feature>                set features.<name>=false
  ring-test                              play the configured sound once
  install       [--scope …]              register hooks
  uninstall     [--scope …] [--legacy]   remove our hooks (optionally also legacy ones)
  youtube       <url>                    start YouTube feature for this session
  youtube-stop                           stop YouTube server for this session

This script is invoked by SKILL.md. Interactive prompts (wizard) live in
SKILL.md and are driven by Claude — comeback.py stays non-interactive so it
works the same from a shell or a hook.
"""

import argparse
import os
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PY = os.path.join(SKILL_DIR, "config.py")
INSTALL_PY = os.path.join(SKILL_DIR, "install.py")
YT_LAUNCH = os.path.join(SKILL_DIR, "youtube", "launch.sh")

FEATURES = ("focus", "ring", "youtube")


def _run(cmd, **kw):
    return subprocess.run(cmd, **kw)


def _config_call(args, capture=False):
    cmd = ["python3", CONFIG_PY] + args
    if capture:
        return _run(cmd, capture_output=True, text=True)
    return _run(cmd)


def _config_get(key, cwd):
    r = _config_call(["--get", key, "--cwd", cwd], capture=True)
    return r.stdout.strip()


def _exists_any():
    cwd = os.getcwd()
    local = os.path.join(cwd, ".claude", "comeback.json")
    glob = os.path.expanduser("~/.claude/comeback.json")
    return os.path.exists(local) or os.path.exists(glob)


def cmd_status(_):
    import json as _json
    cwd = os.getcwd()
    r = _config_call(["--show", "--cwd", cwd], capture=True)
    try:
        data = _json.loads(r.stdout)
    except Exception:
        sys.stdout.write(r.stdout)
        return

    cfg = data.get("config", {})
    source = data.get("source", "?")
    features = cfg.get("features", {})
    ring_cfg = cfg.get("ring", {})
    target = cfg.get("target", {})

    ck = subprocess.run(["cksum"], input=(cwd + "\n").encode(), capture_output=True)
    try:
        hashval = int(ck.stdout.split()[0])
    except Exception:
        hashval = 0
    session_file = f"/tmp/comeback-session-{hashval}.env"
    port = 7000 + (hashval % 2000)
    yt_file = f"/tmp/comeback-youtube-{port}.env"

    on, off = "✓", "✗"

    print(f"comeback  ·  {source}\n")

    # focus
    f_on = features.get("focus", False)
    mode = target.get("mode", "auto")
    focus_detail = ""
    if f_on and mode == "fixed":
        app = target.get("app") or ""
        proj = target.get("project_path") or ""
        focus_detail = f"  →  fixed: {app} {proj}".rstrip()
    print(f"  focus    {on if f_on else off}{focus_detail}")

    # ring
    r_on = features.get("ring", False)
    ring_detail = ""
    if r_on:
        snd = ring_cfg.get("sound_file") or ""
        vol = ring_cfg.get("volume", 1.0)
        ring_detail = f"  →  {os.path.basename(snd)}  vol {vol}"
    print(f"  ring     {on if r_on else off}{ring_detail}")

    # youtube
    y_on = features.get("youtube", False)
    yt_detail = f"  →  porta {port}" if y_on else ""
    print(f"  youtube  {on if y_on else off}{yt_detail}")

    # session
    print()
    if os.path.exists(session_file):
        try:
            env = dict(line.strip().split("=", 1) for line in open(session_file) if "=" in line)
            proj = os.path.basename(env.get("PROJECT", ""))
            caller = env.get("CALLER", "?")
            print(f"  sessione attiva  ·  {caller} → {proj}")
        except Exception:
            print("  sessione attiva")
    else:
        print("  nessuna sessione attiva (avvia/riavvia Claude per registrarla)")

    if y_on:
        print(f"  youtube  {'in riproduzione' if os.path.exists(yt_file) else 'fermo'}")

    print()
    print("Comandi: /comeback enable|disable FEATURE  ·  /comeback config  ·  /comeback ring test")


def cmd_config_exists(_):
    sys.exit(0 if _exists_any() else 1)


def cmd_config_init(args):
    _config_call(["--init", "--scope", args.scope])


def cmd_config_set(args):
    _config_call(["--set", args.kv, "--scope", args.scope])


def _toggle(feature, value, scope):
    if feature not in FEATURES:
        sys.exit(f"Feature sconosciuta: {feature}. Valide: {', '.join(FEATURES)}")
    _config_call(["--set", f"features.{feature}={'true' if value else 'false'}", "--scope", scope])


def cmd_enable(args):
    _toggle(args.feature, True, args.scope)


def cmd_disable(args):
    _toggle(args.feature, False, args.scope)


def cmd_ring_test(_):
    cwd = os.getcwd()
    sound = _config_get("ring.sound_file", cwd) or "/System/Library/Sounds/Glass.aiff"
    vol = _config_get("ring.volume", cwd) or "1.0"
    if not os.path.exists(sound):
        sys.exit(f"✗ Sound file non trovato: {sound}")
    subprocess.run(["afplay", "-v", vol, sound])
    print(f"✓ Riprodotto: {sound} (vol {vol})")


def cmd_install(args):
    cmd = ["python3", INSTALL_PY]
    if args.scope:
        cmd += ["--scope", args.scope]
    _run(cmd)


def cmd_uninstall(args):
    cmd = ["python3", INSTALL_PY, "--uninstall"]
    if args.scope:
        cmd += ["--scope", args.scope]
    if args.legacy:
        cmd += ["--legacy"]
    _run(cmd)


def cmd_youtube(args):
    if not os.access(YT_LAUNCH, os.X_OK):
        os.chmod(YT_LAUNCH, 0o755)
    _run(["bash", YT_LAUNCH, args.url])


def cmd_youtube_stop(_):
    _run(["bash", YT_LAUNCH, "stop"])


def main():
    p = argparse.ArgumentParser(prog="comeback")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("config-exists").set_defaults(fn=cmd_config_exists)

    ci = sub.add_parser("config-init")
    ci.add_argument("--scope", choices=("global", "local"), default="global")
    ci.set_defaults(fn=cmd_config_init)

    cs = sub.add_parser("config-set")
    cs.add_argument("kv", help="key=value")
    cs.add_argument("--scope", choices=("global", "local"), default="global")
    cs.set_defaults(fn=cmd_config_set)

    en = sub.add_parser("enable")
    en.add_argument("feature", choices=FEATURES)
    en.add_argument("--scope", choices=("global", "local"), default="global")
    en.set_defaults(fn=cmd_enable)

    di = sub.add_parser("disable")
    di.add_argument("feature", choices=FEATURES)
    di.add_argument("--scope", choices=("global", "local"), default="global")
    di.set_defaults(fn=cmd_disable)

    sub.add_parser("ring-test").set_defaults(fn=cmd_ring_test)

    ins = sub.add_parser("install")
    ins.add_argument("--scope", choices=("global", "local"), default=None)
    ins.set_defaults(fn=cmd_install)

    un = sub.add_parser("uninstall")
    un.add_argument("--scope", choices=("global", "local"), default=None)
    un.add_argument("--legacy", action="store_true")
    un.set_defaults(fn=cmd_uninstall)

    yt = sub.add_parser("youtube")
    yt.add_argument("url")
    yt.set_defaults(fn=cmd_youtube)

    sub.add_parser("youtube-stop").set_defaults(fn=cmd_youtube_stop)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
