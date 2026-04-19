#!/usr/bin/env python3
"""comeback — configuration load/save/get/set + feature gating.

Lookup order (first hit wins, no merge):
  1. <cwd>/.claude/comeback.json
  2. ~/.claude/comeback.json

CLI (used by hooks and bmt-like callers):
  config.py --feature NAME --cwd PATH     exit 0 if enabled, 1 otherwise
  config.py --get dotted.key --cwd PATH   print value, empty if missing
  config.py --set key=value --scope SCOPE write to global|local
  config.py --show --cwd PATH             JSON dump of resolved config + source
  config.py --init --scope SCOPE          create default template (won't overwrite)
  config.py --path --scope SCOPE          print target path for that scope
"""

import argparse
import json
import os
import sys

LOG = "/tmp/comeback.log"

DEFAULTS = {
    "version": 1,
    "features": {
        "focus": True,
        "ring": False,
        "youtube": False,
    },
    "ring": {
        "sound_file": "/System/Library/Sounds/Glass.aiff",
        "volume": 1.0,
    },
    "target": {
        "mode": "auto",
        "app": None,
        "project_path": None,
    },
}

GLOBAL_PATH = os.path.expanduser("~/.claude/comeback.json")


def local_path(cwd):
    return os.path.join(cwd, ".claude", "comeback.json")


def _log(msg):
    try:
        with open(LOG, "a") as f:
            f.write(f"[config] {msg}\n")
    except Exception:
        pass


def _read(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        _log(f"malformed JSON at {path}: {e}")
        return None
    except Exception as e:
        _log(f"read error {path}: {e}")
        return None


def _merge_defaults(cfg):
    """Shallow-fill missing top-level keys so dotted-key reads never KeyError."""
    if not isinstance(cfg, dict):
        return dict(DEFAULTS)
    out = {k: v for k, v in DEFAULTS.items()}
    for k, v in cfg.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            merged = dict(out[k])
            merged.update(v)
            out[k] = merged
        else:
            out[k] = v
    return out


def resolve(cwd):
    """Return (config_dict, source_path_or_None). Missing → defaults, None."""
    if cwd:
        lp = local_path(cwd)
        cfg = _read(lp)
        if cfg is not None:
            return _merge_defaults(cfg), lp
    cfg = _read(GLOBAL_PATH)
    if cfg is not None:
        return _merge_defaults(cfg), GLOBAL_PATH
    return dict(DEFAULTS), None


def _dot_get(cfg, key):
    cur = cfg
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _dot_set(cfg, key, value):
    parts = key.split(".")
    cur = cfg
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _coerce(value):
    """Minimal string→python coercion for CLI --set values."""
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none"):
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _target_path(scope, cwd):
    if scope == "global":
        return GLOBAL_PATH
    if scope == "local":
        if not cwd:
            raise SystemExit("--scope local requires --cwd")
        return local_path(cwd)
    raise SystemExit(f"unknown scope: {scope}")


def _write(path, cfg):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def cmd_feature(args):
    cfg, _ = resolve(args.cwd)
    enabled = bool(_dot_get(cfg, f"features.{args.feature}"))
    sys.exit(0 if enabled else 1)


def cmd_get(args):
    cfg, _ = resolve(args.cwd)
    val = _dot_get(cfg, args.get)
    if val is None:
        return
    if isinstance(val, bool):
        print("true" if val else "false")
    else:
        print(val)


def cmd_set(args):
    if "=" not in args.set:
        raise SystemExit("--set expects key=value")
    key, value = args.set.split("=", 1)
    path = _target_path(args.scope, args.cwd)
    cfg = _read(path) or {}
    cfg = _merge_defaults(cfg) if cfg else dict(DEFAULTS)
    _dot_set(cfg, key, _coerce(value))
    _write(path, cfg)
    print(f"✓ {key} = {value}  ({path})")


def cmd_show(args):
    cfg, source = resolve(args.cwd)
    print(json.dumps({"config": cfg, "source": source}, indent=2))


def cmd_init(args):
    path = _target_path(args.scope, args.cwd)
    if os.path.exists(path):
        print(f"Config già esistente: {path}")
        return
    _write(path, DEFAULTS)
    print(f"✓ Config creata: {path}")


def cmd_path(args):
    print(_target_path(args.scope, args.cwd))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--feature")
    p.add_argument("--get")
    p.add_argument("--set")
    p.add_argument("--show", action="store_true")
    p.add_argument("--init", action="store_true")
    p.add_argument("--path-only", action="store_true")
    p.add_argument("--cwd", default=os.getcwd())
    p.add_argument("--scope", choices=("global", "local"), default="global")
    args = p.parse_args()

    if args.feature:
        cmd_feature(args)
    elif args.get:
        cmd_get(args)
    elif args.set:
        cmd_set(args)
    elif args.show:
        cmd_show(args)
    elif args.init:
        cmd_init(args)
    elif args.path_only:
        cmd_path(args)
    else:
        p.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
