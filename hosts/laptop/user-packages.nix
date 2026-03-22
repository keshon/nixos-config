# hosts/laptop/user-packages.nix — nixctl pkg add/remove edits this file
# Nix: end the package list with `]` only (no `;` after the bracket).
{ pkgs, ... }:
with pkgs; [
  discord
  telegram-desktop
]
