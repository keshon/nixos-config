#!/usr/bin/env python3
"""
nixctl — NixOS control center
══════════════════════════════

First run
  nixctl bootstrap              first-time setup on a new machine (wizard)
  nixctl bootstrap --resume [HOST]   continue after a failed step (no wizard)

System
  nixctl sys rebuild            rebuild the system
  nixctl sys update             update flake.lock + rebuild
  nixctl sys check              dry-run, no changes applied
  nixctl sys rollback           roll back to previous generation
  nixctl sys gc                 delete old generations
  nixctl sys generations        list generation history

Packages
  nixctl pkg search <query>     search package (local cache → network)
  nixctl pkg search <q> --fresh force network search
  nixctl pkg add    <n>         add package to packages.nix
  nixctl pkg remove <n>         remove package from packages.nix
  nixctl pkg list               list installed packages

Config repo (hosts, flake)
  nixctl host list              list all hosts (active marked ★)
  nixctl host new  <n> [--from <ref>]  create host (template = references/<ref>/)
  nixctl host use  <n>          [advanced] edit another machine's packages without switching hardware
  nixctl host remove <n>        remove host
  nixctl host info [<n>]        show host status

  nixctl self status            short git summary
  nixctl self sync              git pull --rebase (config repo)
  nixctl self bump              nix flake lock (refresh pinned inputs)
  nixctl self push [message]    commit and push config changes

Other
  nixctl dconf apply            dump dconf + insert into home.nix
  nixctl dconf apply --select   same, with interactive section picker
  nixctl dconf dump             only save to dconf-backup.txt

  nixctl backup save            create a config snapshot
  nixctl backup list            list snapshots
  nixctl backup restore [n]     restore snapshot

  nixctl cache export <path>    export system closure to local cache
  nixctl cache import <path>    rebuild using local cache (offline)

Advanced
  nixctl reference list         alias: list reference profiles (same as templates for host new / bootstrap)
  nixctl doctor                 flake lock, delivery path, repo health

Flags:
  --host <name>   override target host (sys commands)
  --fresh         force network search (pkg search)
  -h, --help      show command help

Configuration:
  By default nixctl looks for your config in ~/nixos/.
  Override with: NIXCTL_DIR=/path/to/config nixctl <command>
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROUTES = {
    "sys":       "modules.sys",
    "host":      "modules.host",
    "reference": "modules.reference",
    "pkg":       "modules.pkg",
    "dconf":     "modules.dconf",
    "backup":    "modules.backup",
    "cache":     "modules.cache",
    "bootstrap": "modules.bootstrap",
    "self":      "modules.self",
    "doctor":    "modules.doctor",
}


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return

    group    = args[0]
    sub_args = args[1:]

    if group not in ROUTES:
        print(f"  Unknown command: {group}")
        print(f"  Available: {', '.join(ROUTES)}")
        print("\n  Help: nixctl --help")
        sys.exit(1)

    import importlib
    mod = importlib.import_module(ROUTES[group])
    mod.run(sub_args)


if __name__ == "__main__":
    main()
