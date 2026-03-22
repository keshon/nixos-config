# hosts/desktop/user-packages.nix — nixctl pkg add/remove edits this file
# Nix: end the package list with `]` only (no `;` after the bracket).
{ pkgs, ... }:
with pkgs; [
  vlc
  tixati
  discord
  handbrake
  mkvtoolnix
  telegram-desktop
  go

  # v2ray
  xray
  v2rayn
  v2ray-geoip
  v2ray-domain-list-community
]
