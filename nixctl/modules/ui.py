"""
Shared CLI output: context line and help tiers (English, ASCII).
"""

from __future__ import annotations

import sys


def get_context_line() -> str:
    """One-line session context: machine, software profile, flake target."""
    import modules.config as cfg

    m = cfg.get_machine()
    profile = cfg.get_environment()
    ft = cfg.flake_target()
    return f"nixctl | machine={m} | profile={profile} | {ft}"


def print_context(file=sys.stderr) -> None:
    try:
        print(get_context_line(), file=file)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tiered help (root = short; --help = full)
# ---------------------------------------------------------------------------

SHORT_HELP = """\
nixctl — NixOS configuration helper

Usage:
  nixctl <group> [arguments ...]
  nixctl <group> --help

Groups:
  bootstrap   First-time setup (wizard)
  sys         Rebuild, update, rollback, garbage-collect
  pkg         Search, add, remove packages
  host        Flake machines, profiles, and flake.nix entries
  git, self   Git status, pull, flake lock, push
  dconf       Desktop settings into home.nix
  backup      Rotate snapshots of the config tree
  cache       Export / import local Nix store cache
  reference   List reference profiles (templates)

Config directory: ~/nixos/  (override with NIXCTL_DIR)

For the full command list:  nixctl --help
"""


FULL_HELP = """\
nixctl — NixOS configuration helper

First run
  nixctl bootstrap
  nixctl bootstrap --resume [HOST]

System
  nixctl sys rebuild
  nixctl sys update
  nixctl sys check
  nixctl sys rollback
  nixctl sys gc
  nixctl sys generations

Packages
  nixctl pkg search [query]
  nixctl pkg add <name>
  nixctl pkg remove <name>
  nixctl pkg list
  nixctl pkg verify          # nix build system (no switch); after edits, use to catch errors

Flake / machines
  nixctl host list
  nixctl host new <name> [--from <ref>]
  nixctl host use <name>
  nixctl host remove <name>
  nixctl host info [<name>]

Git (config repo)
  nixctl git status
  nixctl git sync
  nixctl git bump
  nixctl git push [message]
  (alias: nixctl self ...)

Other
  nixctl dconf apply
  nixctl dconf apply --select
  nixctl dconf dump

  nixctl backup save
  nixctl backup list
  nixctl backup restore [n]

  nixctl cache export <path>
  nixctl cache import <path>

  nixctl reference list

  -h, --help    show this full help

Configuration:
  Default config path: ~/nixos/
  Override: NIXCTL_DIR=/path/to/config nixctl <command>
"""
