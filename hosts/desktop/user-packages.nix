# hosts/desktop/user-packages.nix — nixctl pkg add/remove edits this file
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
];
