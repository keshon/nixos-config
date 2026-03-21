#!/usr/bin/env bash
# bootstrap.sh — first-time NixOS setup
#
# Usage on a fresh system:
#   nix-shell -p git --run "git clone https://github.com/keshon/nixos-config ~/nixos"
#   bash ~/nixos/bootstrap.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NIXCTL_PY="$SCRIPT_DIR/nixctl/nixctl.py"
NIXCTL_REPO="https://github.com/keshon/nixctl"

# ---------------------------------------------------------------------------
# Ensure git is available
# ---------------------------------------------------------------------------
if ! command -v git &>/dev/null; then
    echo "[bootstrap] git not found, restarting via nix-shell..."
    exec nix-shell -p git python3 --run "bash '$0' $*"
fi

# ---------------------------------------------------------------------------
# Run nixctl: prefer flake (no git submodule), else clone + python
# ---------------------------------------------------------------------------
if command -v nix &>/dev/null; then
    echo "[bootstrap] using nix run github:keshon/nixctl (flake delivery)"
    export NIXCTL_DIR="$SCRIPT_DIR"
    # Installer / fresh systems often lack nix.conf features; bootstrap runs before your flake applies.
    # --no-write-lock-file: remote flake is read-only; Nix must not try to update its lock in the store.
    exec nix --extra-experimental-features "nix-command flakes" run --no-write-lock-file "github:keshon/nixctl" -- bootstrap "$@"
fi

if [ ! -f "$NIXCTL_PY" ]; then
    echo "[bootstrap] nix not available — cloning nixctl repo next to config..."
    git clone --depth=1 "$NIXCTL_REPO" "$SCRIPT_DIR/nixctl"
fi

if ! command -v python3 &>/dev/null; then
    echo "[bootstrap] python3 not found, restarting via nix-shell..."
    exec nix-shell -p git python3 --run "bash '$0' $*"
fi

export NIXCTL_DIR="$SCRIPT_DIR"
exec python3 "$NIXCTL_PY" bootstrap "$@"
