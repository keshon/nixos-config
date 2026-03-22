#!/usr/bin/env python3
"""nixctl — NixOS configuration helper (see modules.ui.FULL_HELP)."""

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
    "git":       "modules.git",
    "self":      "modules.git",
}


def main():
    args = sys.argv[1:]

    import modules.ui as ui

    if not args:
        ui.print_context()
        print(ui.SHORT_HELP)
        return

    if args[0] in ("-h", "--help", "help"):
        ui.print_context()
        print(ui.FULL_HELP)
        return

    group = args[0]
    sub_args = args[1:]

    if group not in ROUTES:
        ui.print_context()
        print(f"error: unknown command {group!r}")
        print(f"  Available: {', '.join(sorted(ROUTES.keys()))}")
        print("  Run: nixctl --help")
        sys.exit(1)

    ui.print_context()

    import importlib
    mod = importlib.import_module(ROUTES[group])
    mod.run(sub_args)


if __name__ == "__main__":
    main()
