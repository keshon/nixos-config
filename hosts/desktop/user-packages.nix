# hosts/desktop/user-packages.nix — nixctl pkg add/remove edits this file
# Nix: close with `]` only (no `;` after `]`) — `with pkgs; [ … ]` is the whole file body.
{ pkgs, ... }:
with pkgs; [
  vlc
  tixati
  discord
  handbrake
  mkvtoolnix
  telegram-desktop

  # v2ray
  xray
  v2rayn
  v2ray-geoip
  v2ray-domain-list-community
]
