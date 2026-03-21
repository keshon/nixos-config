# hosts/laptop/user-packages.nix — nixctl pkg add/remove edits this file
{ pkgs, ... }:
with pkgs; [
  kora-icon-theme
  marble-shell-theme

  discord
  telegram-desktop
];
