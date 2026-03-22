"""
modules/reference.py — reference profiles (references/<name>/home.nix)

nixctl reference list
"""

import os

from .config import REFERENCES_DIR, REFERENCE_DEFAULT

HELP = """\
nixctl reference <command>

  list    list profiles under references/<name>/home.nix

  (Templates are also listed in `nixctl bootstrap` and `nixctl host new --from <ref>`.)
"""


def run(args: list):
    if not args or args[0] in ("-h", "--help"):
        print(HELP)
        return

    cmd = args[0]
    if cmd == "list":
        list_references()
    else:
        print(f"  Unknown command: reference {cmd}")
        print(HELP)


def discover_references() -> list[str]:
    """Names under REFERENCES_DIR that have references/<name>/home.nix."""
    if not os.path.isdir(REFERENCES_DIR):
        return []
    names = []
    for name in sorted(os.listdir(REFERENCES_DIR)):
        path = os.path.join(REFERENCES_DIR, name)
        hm = os.path.join(path, "home.nix")
        if os.path.isdir(path) and os.path.isfile(hm):
            names.append(name)
    return names


def list_references():
    if not os.path.isdir(REFERENCES_DIR):
        print(f"  No references directory: {REFERENCES_DIR}")
        print(f"  Create references/{REFERENCE_DEFAULT}/home.nix to add profiles.")
        return

    names = discover_references()

    if not names:
        print(f"  No references found (expected references/<name>/home.nix under {REFERENCES_DIR})")
        return

    print(f"  References ({len(names)}):")
    for n in names:
        mark = " (default)" if n == REFERENCE_DEFAULT else ""
        print(f"    - {n}{mark}")
