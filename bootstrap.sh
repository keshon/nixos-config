#!/usr/bin/env bash
# bootstrap.sh — first-time NixOS setup
#
# Usage on a fresh system:
#   nix-shell -p git --run "git clone https://github.com/keshon/nixos-config ~/nixos"
#   bash ~/nixos/bootstrap.sh
#
# After a failed step (e.g. rebuild error), fix the config and re-run:
#   bash ~/nixos/bootstrap.sh --resume vbox
#   HOST optional if ~/.nixos/.nixctl-store already has host / machine

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NIXCTL_PY="$SCRIPT_DIR/nixctl/nixctl.py"

# ---------------------------------------------------------------------------
# Ensure git is available
# ---------------------------------------------------------------------------
if ! command -v git &>/dev/null; then
    echo "[bootstrap] git not found, restarting via nix-shell..."
    exec nix-shell -p git python3 --run "bash '$0' $*"
fi

# ---------------------------------------------------------------------------
# Run nixctl: flake in ./nixctl (same repo), else python
# ---------------------------------------------------------------------------
if command -v nix &>/dev/null; then
    export NIXCTL_DIR="$SCRIPT_DIR"
    if [ -f "$SCRIPT_DIR/nixctl/flake.nix" ]; then
        echo "[bootstrap] using nix run $SCRIPT_DIR/nixctl"
        exec nix --extra-experimental-features "nix-command flakes" run --no-write-lock-file "$SCRIPT_DIR/nixctl" -- bootstrap "$@"
    fi
    echo "[bootstrap] error: missing $SCRIPT_DIR/nixctl/flake.nix (incomplete checkout?)" >&2
    exit 1
fi

if [ ! -f "$NIXCTL_PY" ]; then
    echo "[bootstrap] error: missing $NIXCTL_PY — use a full clone of this repository." >&2
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "[bootstrap] python3 not found, restarting via nix-shell..."
    exec nix-shell -p git python3 --run "bash '$0' $*"
fi

export NIXCTL_DIR="$SCRIPT_DIR"
exec python3 "$NIXCTL_PY" bootstrap "$@"
