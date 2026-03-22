#!/usr/bin/env bash
# Rewrite hosts/<name>/boot.nix to UEFI + systemd-boot (no GRUB).
# Use when the wrong bootloader was chosen at bootstrap (e.g. GRUB on a UEFI laptop).
#
# Usage:
#   ./scripts/set-boot-uefi.sh [HOST]
#   HOST defaults to machine in ~/nixos/.nixctl-store (machine=) or basename of hostname.
#
# Then: sudo nixos-rebuild switch --flake ~/nixos#HOST

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NIXOS_DIR="${NIXCTL_DIR:-$HOME/nixos}"
if [[ -d "$REPO_ROOT/hosts" ]]; then
  NIXOS_DIR="$REPO_ROOT"
fi

STORE="$NIXOS_DIR/.nixctl-store"
HOST="${1:-}"
if [[ -z "$HOST" ]] && [[ -f "$STORE" ]]; then
  HOST="$(grep -o '"machine"[[:space:]]*:[[:space:]]*"[^"]*"' "$STORE" 2>/dev/null | sed 's/.*"\([^"]*\)".*/\1/' || true)"
fi
if [[ -z "$HOST" ]]; then
  HOST="$(hostname -s 2>/dev/null | sed 's/^nixos-//' || echo "")"
fi
if [[ -z "$HOST" ]]; then
  echo "usage: $0 <flake-host-name>" >&2
  echo "  or set machine in $STORE" >&2
  exit 1
fi

BOOT="$NIXOS_DIR/hosts/$HOST/boot.nix"
if [[ ! -f "$BOOT" ]]; then
  echo "error: not found: $BOOT" >&2
  exit 1
fi

cp -a "$BOOT" "${BOOT}.bak.$(date +%Y%m%d%H%M%S)"
cat >"$BOOT" <<EOF
# hosts/$HOST/boot.nix — UEFI + systemd-boot (rewritten by scripts/set-boot-uefi.sh)
{ ... }:

{
  # UEFI bootloader
  boot.loader.systemd-boot.enable      = true;
  boot.loader.efi.canTouchEfiVariables = true;
}
EOF

echo "done: wrote $BOOT (backup beside it)"
echo "  next: sudo nixos-rebuild switch --flake $NIXOS_DIR#$HOST"
