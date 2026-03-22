"""
self.py — repo sync and flake input updates

nixctl self status   short git summary (see nixctl doctor for details)
nixctl self sync     git pull --rebase for the config repo (no submodule)
nixctl self bump     nix flake lock (refresh pinned inputs)
nixctl self push     commit and push config repo changes

Legacy: self pull → sync; submodule workflows removed from defaults.
"""

import os
import subprocess

from .config import NIXOS_DIR, confirm

HELP = """\
nixctl self <command>

  status   short repo summary
  sync     pull config repo (git pull --rebase) — happy path
  bump     refresh flake.lock (nixpkgs, home-manager, …)
  push     commit and push config repo changes

Legacy aliases:
  pull     same as sync
  update   same as bump
"""


def run(args: list):
    if not args or args[0] in ("-h", "--help"):
        print(HELP)
        return

    cmd = args[0]
    dispatch = {
        "status": status,
        "sync":   sync,
        "pull":   pull,
        "bump":   bump,
        "update": bump,
        "push":   lambda: push(args[1:]),
    }

    if cmd not in dispatch:
        print(f"  Unknown command: self {cmd}")
        print(HELP)
        return

    dispatch[cmd]()


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def status():
    print("  nixos-config (short)")
    print(f"  {'─' * 38}")

    branch = _git(NIXOS_DIR, ["rev-parse", "--abbrev-ref", "HEAD"])
    print(f"  Branch   : {branch or '?'}")

    last = _git(NIXOS_DIR, ["log", "-1", "--format=%h  %s  (%ar)"])
    print(f"  Commit   : {last or '?'}")

    _git(NIXOS_DIR, ["fetch", "--quiet"], silent=True)
    ahead  = _git(NIXOS_DIR, ["rev-list", "--count", "HEAD..@{u}"])
    behind = _git(NIXOS_DIR, ["rev-list", "--count", "@{u}..HEAD"])
    if ahead and ahead != "0":
        print(f"  Upstream : {ahead} new commit(s) available  ← nixctl self sync")
    elif behind and behind != "0":
        print(f"  Upstream : {behind} local commit(s) not pushed  ← nixctl self push")
    else:
        print(f"  Upstream : up to date")

    dirty = _git(NIXOS_DIR, ["status", "--short"])
    if dirty:
        print(f"  Changes  :")
        for line in dirty.splitlines():
            print(f"    {line}")
    else:
        print(f"  Changes  : none")

    print()
    print("  For flake.lock refresh: nixctl doctor  |  nixctl self bump")


# ---------------------------------------------------------------------------
# sync (pull config only)
# ---------------------------------------------------------------------------

def sync():
    print("  → git pull --rebase (config repo)...")
    code = _run(NIXOS_DIR, ["git", "pull", "--rebase"])

    if code != 0:
        print()
        print("  ✗ Pull failed — there may be conflicts.")
        print("    Options:")
        print("    • Discard local changes : git -C ~/nixos checkout -- .")
        print("    • Stash local changes   : git -C ~/nixos stash")
        print("    • See what conflicts    : git -C ~/nixos status")
        return

    print("  ✓ Done")

    changed = _git(NIXOS_DIR, ["diff", "HEAD@{1}", "--name-only"]) or ""
    nix_changed = [f for f in changed.splitlines() if f.endswith(".nix")]
    if nix_changed:
        print()
        print(f"  Changed .nix files ({len(nix_changed)}):")
        for f in nix_changed[:8]:
            print(f"    • {f}")
        if len(nix_changed) > 8:
            print(f"    ... and {len(nix_changed) - 8} more")
        print()
        if confirm("Apply changes? (nixctl sys rebuild)", default=True):
            from .sys import rebuild
            rebuild()


def pull():
    """Backward-compatible alias for sync."""
    sync()


# ---------------------------------------------------------------------------
# bump — refresh flake.lock (nixctl is bundled in ./nixctl, not a separate input)
# ---------------------------------------------------------------------------

def bump():
    print("  → nix flake lock …")
    code = _run(NIXOS_DIR, ["nix", "flake", "lock"])
    if code != 0:
        print("  ✗ flake lock failed")
        return
    print("  ✓ flake.lock updated")
    print()
    print("  Rebuild if needed: nixctl sys rebuild")


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------

def push(extra_args: list):
    dirty = _git(NIXOS_DIR, ["status", "--short"])
    if not dirty:
        print("  Nothing to commit — working tree is clean")
        return

    print("  Changes to commit:")
    for line in dirty.splitlines():
        print(f"    {line}")
    print()

    if extra_args:
        msg = " ".join(extra_args)
    else:
        msg = input("  Commit message [update configs]: ").strip()
        if not msg:
            msg = "update configs"

    _run(NIXOS_DIR, ["git", "add", "-A"])

    code = _run(NIXOS_DIR, ["git", "commit", "-m", msg])
    if code != 0:
        print("  ✗ Commit failed")
        return

    print("  → Pushing...")
    code = _run(NIXOS_DIR, ["git", "push"])
    if code == 0:
        print("  ✓ Pushed")
    else:
        print("  ✗ Push failed")
        print("    Try: git -C ~/nixos push --set-upstream origin main")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cwd: str, cmd: list) -> int:
    return subprocess.run(cmd, cwd=cwd).returncode


def _git(cwd: str, args: list, silent: bool = False) -> str | None:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        if result.returncode != 0 and not silent:
            return None
        return result.stdout.strip() or None
    except Exception:
        return None
