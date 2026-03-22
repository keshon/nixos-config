# hosts/laptop/user-packages.nix — nixctl pkg add/remove edits this file
{ pkgs, ... }:
with pkgs; [
  discord
  telegram-desktop
];
