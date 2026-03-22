"""
modules/cache.py — local Nix binary cache (e.g. USB)

nixctl cache export <path>
nixctl cache import <path>
"""

import os
import subprocess

from .config import NIXOS_DIR, exec_shell, flake_target, confirm

HELP = """\
nixctl cache <command>

  export <path>   copy current system closure to a local cache dir
                  example: nixctl cache export /mnt/usb/nix-cache
  import <path>   use that cache as a substituter on the next rebuild
                  example: nixctl cache import /mnt/usb/nix-cache
"""


def run(args: list):
    if not args or args[0] in ("-h", "--help"):
        print(HELP); return

    cmd, rest = args[0], args[1:]

    if cmd == "export":
        if not rest:
            print("  Provide a path: nixctl cache export /mnt/usb/nix-cache"); return
        export(rest[0])
    elif cmd == "import":
        if not rest:
            print("  Provide a path: nixctl cache import /mnt/usb/nix-cache"); return
        cache_import(rest[0])
    elif cmd == "status":
        _status()
    else:
        print(f"  Unknown command: cache {cmd}")
        print(HELP)


def export(dest: str) -> bool:
    os.makedirs(dest, exist_ok=True)

    code, out = exec_shell("readlink -f /run/current-system", capture=True)
    system_path = out.strip()
    if not system_path:
        print("  error: could not resolve /run/current-system"); return False

    print(f"  -> Exporting {system_path}")
    print(f"     to {dest}")
    print("     (this may take several minutes)")

    code, _ = exec_shell(f"nix copy --to 'file://{dest}' '{system_path}'")
    if code == 0:
        print(f"  done: cache exported to {dest}")
        return True
    print(f"  error: nix copy failed (exit {code})")
    return False


def cache_import(src: str) -> bool:
    if not os.path.isdir(src):
        print(f"  error: path not found: {src}"); return False

    target = flake_target()
    print(f"  -> Rebuild with cache: {src}")

    code, _ = exec_shell(
        f"sudo nixos-rebuild switch --flake {target} "
        f"--option substituters 'https://cache.nixos.org file://{src}' "
        f"--option trusted-public-keys "
        f"'cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY='"
    )

    if code == 0:
        print("  done: rebuild with local cache finished")
        return True
    print(f"  error: nixos-rebuild failed (exit {code})")
    return False


def _status():
    code, out = exec_shell("nix show-config 2>/dev/null | grep -E 'substituters|trusted'", capture=True)
    if out.strip():
        print("  Current substituters:")
        for line in out.strip().splitlines():
            print(f"    {line}")
    else:
        print("  Substituters: default (cache.nixos.org)")
