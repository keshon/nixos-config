"""
doctor.py — verify nixctl delivery (bundled in repo) and repo health

nixctl doctor
"""

import os
import subprocess

from .config import NIXOS_DIR, FLAKE_NIX

HELP = """\
nixctl doctor

  Summarize config repo state, nixctl tree, and git status.
  nixctl is built from ./nixctl in this flake (see flake.nix).
"""


def run(args: list):
    if args and args[0] in ("-h", "--help"):
        print(HELP)
        return
    doctor()


def doctor():
    print("  nixctl doctor")
    print(f"  {'─' * 40}")
    print(f"  NIXCTL_DIR : {NIXOS_DIR}")
    print(f"  flake.nix  : {'ok' if os.path.isfile(FLAKE_NIX) else 'missing'}")

    lock = os.path.join(NIXOS_DIR, "flake.lock")
    if os.path.isfile(lock):
        print("  flake.lock : present")
    else:
        print("  flake.lock : missing")

    sub = os.path.join(NIXOS_DIR, "nixctl")
    if os.path.isdir(sub):
        print("  nixctl/    : present (bundled — built by flake.nix from ./nixctl)")
    else:
        print("  nixctl/    : absent (expected at ./nixctl in the config repo)")

    print()
    print("  Delivery: flake.nix defines `nixctl` and passes it via specialArgs;")
    print("            hosts/<host>/packages.nix uses `{ pkgs, nixctl, ... }`.")
    print("            Refresh inputs: nixctl self bump")
    print()

    try:
        result = subprocess.run(
            ["git", "-C", NIXOS_DIR, "status", "--short"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            print("  Git (config repo):")
            for line in result.stdout.strip().splitlines()[:12]:
                print(f"    {line}")
        elif result.returncode == 0:
            print("  Git: working tree clean")
    except Exception:
        pass
