"""
modules/git.py — git operations on the config repo (like git status / pull / push)

nixctl git status   short git summary
nixctl git sync     git pull --rebase for the config repo
nixctl git bump     nix flake lock (refresh pinned inputs)
nixctl git push     commit and push config repo changes

Legacy alias: nixctl self … (same module)
"""

import os
import subprocess

from .config import NIXOS_DIR, confirm

HELP = """\
nixctl git <command>

  status   short repo summary
  sync     pull config repo (git pull --rebase) — happy path
  bump     refresh flake.lock (nixpkgs, home-manager, …)
  push     commit and push config repo changes

Legacy aliases:
  pull     same as sync
  update   same as bump

Auth:
  status / sync / bump use read-only Git + Nix (no login for public flakes).
  push always needs GitHub auth: use SSH remote, or HTTPS + a personal access
  token (GitHub no longer accepts account passwords over HTTPS).
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
        print(f"  Unknown command: git {cmd}")
        print(HELP)
        return

    dispatch[cmd]()


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def status():
    print("  nixos-config (short)")
    print(f"  {'-' * 38}")

    branch = _git(NIXOS_DIR, ["rev-parse", "--abbrev-ref", "HEAD"])
    print(f"  Branch   : {branch or '?'}")

    last = _git(NIXOS_DIR, ["log", "-1", "--format=%h  %s  (%ar)"])
    print(f"  Commit   : {last or '?'}")

    _git(NIXOS_DIR, ["fetch", "--quiet"], silent=True, no_prompt=True)
    ahead  = _git(NIXOS_DIR, ["rev-list", "--count", "HEAD..@{u}"])
    behind = _git(NIXOS_DIR, ["rev-list", "--count", "@{u}..HEAD"])
    if ahead and ahead != "0":
        print(f"  Upstream : {ahead} new commit(s) available  (run: nixctl git sync)")
    elif behind and behind != "0":
        print(f"  Upstream : {behind} local commit(s) not pushed  (run: nixctl git push)")
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
    print("  Refresh flake.lock: nixctl git bump")


# ---------------------------------------------------------------------------
# sync (pull config only)
# ---------------------------------------------------------------------------

def sync():
    print("  -> git pull --rebase (config repo)...")
    code = _run(NIXOS_DIR, ["git", "pull", "--rebase"], env=_env_no_git_prompt())

    if code != 0:
        print()
        print("  error: pull failed (resolve conflicts and retry).")
        print("    Options:")
        print("    • Discard local changes : git -C ~/nixos checkout -- .")
        print("    • Stash local changes   : git -C ~/nixos stash")
        print("    • See what conflicts    : git -C ~/nixos status")
        return

    print("  done.")

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
    print("  -> nix flake lock ...")
    code = _run(
        NIXOS_DIR,
        ["nix", "flake", "lock"],
        env=_env_no_git_prompt(),
    )
    if code != 0:
        print("  error: flake lock failed")
        print("    If this needs private inputs, run: nix flake lock")
        print("    in a shell where you can authenticate.")
        return
    print("  done: flake.lock updated")
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
        print("  error: commit failed")
        return

    print("  -> pushing...")
    code = _run(NIXOS_DIR, ["git", "push"])
    if code == 0:
        print("  done: pushed")
    else:
        print("  error: push failed")
        print("    Public repo still requires your identity to push.")
        print("    • SSH: git remote set-url origin git@github.com:USER/REPO.git")
        print("    • HTTPS: use a GitHub personal access token (not your password)")
        print("    Try: git -C ~/nixos push --set-upstream origin main")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env_no_git_prompt() -> dict:
    """
    Avoid interactive Git / Git Credential Manager prompts for read-only work
    (fetch, pull on public repos, nix flake lock fetching public flakes).
    Push still uses the normal environment so you can authenticate when needed.
    """
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    env.pop("GIT_ASKPASS", None)
    return env


def _run(cwd: str, cmd: list, *, env: dict | None = None) -> int:
    if env is not None:
        return subprocess.run(cmd, cwd=cwd, env=env).returncode
    return subprocess.run(cmd, cwd=cwd).returncode


def _git(
    cwd: str,
    args: list,
    silent: bool = False,
    *,
    no_prompt: bool = False,
) -> str | None:
    try:
        common = dict(capture_output=True, text=True, cwd=cwd)
        if no_prompt:
            result = subprocess.run(["git"] + args, env=_env_no_git_prompt(), **common)
        else:
            result = subprocess.run(["git"] + args, **common)
        if result.returncode != 0 and not silent:
            return None
        return result.stdout.strip() or None
    except Exception:
        return None
