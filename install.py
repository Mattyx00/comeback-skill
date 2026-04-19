#!/usr/bin/env python3
"""comeback — install / uninstall hooks in Claude Code settings.json.

Usage:
  install.py [--scope global|local]            # register hooks (idempotent)
  install.py --uninstall [--scope ...]         # remove our hooks
  install.py --uninstall --legacy              # also strip old free-time-player hooks

Auto-detects scope when --scope is omitted: if SKILL_DIR lives under
~/.claude/skills → global (~/.claude/settings.json). Otherwise local
(<project>/.claude/settings.json).
"""

import argparse
import json
import os
import sys

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

# Claude Code sets CLAUDE_CONFIG_DIR for non-default accounts (e.g. ~/.claude-account3).
# Fall back to ~/.claude for the default account.
_CLAUDE_DIR = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
GLOBAL_SKILLS = os.path.join(_CLAUDE_DIR, "skills")
GLOBAL_SETTINGS = os.path.join(_CLAUDE_DIR, "settings.json")

EVENTS = [
    ("SessionStart",      "on-session-start.sh"),
    ("UserPromptSubmit",  "on-work.sh"),
    ("PreToolUse",        "on-tool-start.sh"),
    ("PostToolUse",       "on-tool-done.sh"),
    ("Stop",              "on-stop.sh"),
    ("StopFailure",       "on-stop-failure.sh"),
    ("PermissionRequest", "on-permission.sh"),
    ("SessionEnd",        "on-session-end.sh"),
]


def detect_scope():
    if SKILL_DIR.startswith(GLOBAL_SKILLS):
        return "global"
    return "local"


def settings_path(scope):
    if scope == "global":
        return GLOBAL_SETTINGS
    # Explicit --scope local → current working directory's project settings.
    # Auto-detected "local" (skill lives under <project>/.claude/skills/comeback)
    # is handled by detect_scope() returning a derived path via auto_local_path().
    return os.path.join(os.getcwd(), ".claude", "settings.json")


def auto_local_path():
    """When the skill itself lives inside <project>/.claude/skills/*, derive
    the project's settings.json from SKILL_DIR. Otherwise fall back to cwd."""
    # SKILL_DIR is .../<project>/.claude/skills/<name>
    parts = SKILL_DIR.split(os.sep)
    if len(parts) >= 3 and parts[-3] == ".claude" and parts[-2] == "skills":
        project = os.sep.join(parts[:-3]) or os.sep
        return os.path.join(project, ".claude", "settings.json")
    return os.path.join(os.getcwd(), ".claude", "settings.json")


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        sys.exit(f"✗ settings.json corrotto ({path}): {e}")


def save(path, settings):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")


def hook_entry(script):
    return {
        "type": "command",
        "command": f"{SKILL_DIR}/hooks/{script}",
        "async": True,
    }


def _all_hook_commands(event_list):
    for group in event_list:
        for h in group.get("hooks", []):
            yield h


def already_has(event_list, cmd):
    return any(h.get("command") == cmd for h in _all_hook_commands(event_list))


def add_hook(settings, event, script):
    hooks_section = settings.setdefault("hooks", {})
    event_list = hooks_section.setdefault(event, [])
    cmd = f"{SKILL_DIR}/hooks/{script}"
    if already_has(event_list, cmd):
        return False
    event_list.append({"matcher": "*", "hooks": [hook_entry(script)]})
    return True


def _matches_prefix(cmd, prefix):
    return isinstance(cmd, str) and cmd.startswith(prefix)


def remove_hooks_by_prefix(settings, prefix):
    """Remove any hook whose `command` starts with `prefix`. Returns count."""
    removed = 0
    hooks_section = settings.get("hooks", {})
    for event, event_list in list(hooks_section.items()):
        new_list = []
        for group in event_list:
            kept = [h for h in group.get("hooks", []) if not _matches_prefix(h.get("command"), prefix)]
            removed += len(group.get("hooks", [])) - len(kept)
            if kept:
                new_group = dict(group)
                new_group["hooks"] = kept
                new_list.append(new_group)
        if new_list:
            hooks_section[event] = new_list
        else:
            del hooks_section[event]
    return removed


def cmd_install(scope, path=None):
    path = path or settings_path(scope)
    settings = load(path)
    changed = False
    for event, script in EVENTS:
        if add_hook(settings, event, script):
            changed = True
    if changed:
        save(path, settings)
        print(f"✓ Hook comeback registrati ({scope}) in {path}")
    else:
        print(f"✓ Hook comeback già presenti ({scope})")


def cmd_uninstall(scope, legacy, path=None):
    path = path or settings_path(scope)
    if not os.path.exists(path):
        print(f"Nessun {path} — niente da rimuovere.")
        return
    settings = load(path)
    removed = remove_hooks_by_prefix(settings, f"{SKILL_DIR}/hooks/")
    if legacy:
        # Anything whose path contains the legacy skill name
        hooks_section = settings.get("hooks", {})
        for event, event_list in list(hooks_section.items()):
            new_list = []
            for group in event_list:
                kept = [
                    h for h in group.get("hooks", [])
                    if "free-time-player" not in (h.get("command") or "")
                ]
                removed += len(group.get("hooks", [])) - len(kept)
                if kept:
                    g = dict(group); g["hooks"] = kept; new_list.append(g)
            if new_list:
                hooks_section[event] = new_list
            else:
                del hooks_section[event]
    save(path, settings)
    print(f"✓ Rimossi {removed} hook da {path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scope", choices=("global", "local"), default=None)
    p.add_argument("--uninstall", action="store_true")
    p.add_argument("--legacy", action="store_true",
                   help="With --uninstall: also remove old free-time-player hooks")
    args = p.parse_args()

    if args.scope:
        scope = args.scope
        path = None  # use settings_path(scope)
    else:
        scope = detect_scope()
        # Auto-detected: if local, prefer the inferred project path (skill's own
        # .claude/skills/<name> container) over cwd.
        path = None if scope == "global" else auto_local_path()
    if args.uninstall:
        cmd_uninstall(scope, args.legacy, path)
    else:
        cmd_install(scope, path)


if __name__ == "__main__":
    main()
