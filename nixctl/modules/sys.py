"""
sys.py — NixOS system management

nixctl sys rebuild
nixctl sys update
nixctl sys check
nixctl sys rollback
nixctl sys gc
nixctl sys generations
"""

from .config import (
    exec_cmd, exec_shell, flake_target, confirm,
    get_machine, get_store_value, _hostname_guess,
)

HELP = """\
nixctl sys <command> [--host <name>]

  rebuild      rebuild the system (nixos-rebuild switch)
  update       update flake.lock + rebuild
  check        dry-run, no changes applied
  rollback     roll back to previous generation
  gc           delete old generations (asks confirmation)
  generations  list generation history
"""


def run(args: list):
    if not args or args[0] in ("-h", "--help"):
        print(HELP); return

    host = None
    if "--host" in args:
        i = args.index("--host")
        if i + 1 < len(args):
            host = args[i + 1]

    dispatch = {
        "rebuild":     lambda: rebuild(host),
        "update":      lambda: update(host),
        "check":       lambda: check(host),
        "rollback":    rollback,
        "gc":          gc,
        "generations": generations,
    }

    cmd = args[0]
    if cmd not in dispatch:
        print(f"  Unknown command: sys {cmd}")
        print(HELP); return

    dispatch[cmd]()


def rebuild(host: str | None = None) -> int:
    machine = get_machine()
    env     = get_store_value("host") or machine

    if not host and env != machine:
        print()
        print(f"  ⚠  Active environment : {env}")
        print(f"  ⚠  This machine       : {machine}")
        print(f"  ⚠  Will rebuild with packages from '{env}' + hardware from '{machine}'")
        print()
        if not confirm("Continue rebuild?", default=False):
            print("  Cancelled.")
            print(f"  To restore your own environment: nixctl host use {machine}")
            return 1

    target = flake_target(host)
    print(f"  → nixos-rebuild switch ({target})")
    code = exec_cmd(["nixos-rebuild", "switch", "--flake", target], sudo=True)
    _done(code)
    return code


def update(host: str | None = None) -> int:
    print("  → nix flake update...")
    code = exec_cmd(["nix", "flake", "update"])
    if code != 0:
        print(f"  ✗ flake update failed (code {code})")
        return code
    print("  ✓ flake.lock updated")
    return rebuild(host)


def check(host: str | None = None) -> int:
    target = flake_target(host)
    print(f"  → nixos-rebuild dry-activate ({target})")
    code = exec_cmd(["nixos-rebuild", "dry-activate", "--flake", target], sudo=True)
    _done(code)
    return code


def rollback() -> int:
    print("  → nixos-rebuild switch --rollback")
    code = exec_cmd(["nixos-rebuild", "switch", "--rollback"], sudo=True)
    _done(code)
    return code


def gc() -> int:
    print("  → nix-collect-garbage -d")
    if not confirm("Delete all old generations?", default=False):
        print("  Cancelled.")
        return 0
    code = exec_cmd(["nix-collect-garbage", "-d"], sudo=True)
    _done(code)
    return code


def generations() -> int:
    return exec_cmd(["nixos-rebuild", "list-generations"])


def _done(code: int):
    print("  ✓ Done" if code == 0 else f"  ✗ Error (code {code})")
