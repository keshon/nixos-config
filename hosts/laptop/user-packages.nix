# hosts/laptop/user-packages.nix — nixctl pkg add/remove edits this file
# Nix: close with `]` only (no `;` after `]`) when `with pkgs; [ … ]` is the whole file body.
{ pkgs, ... }:
with pkgs; [
  discord
  telegram-desktop
]
