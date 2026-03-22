# references/minimal/home.nix — Home Manager fragment for reference profile "minimal".
# Inherits after repo-wide home.nix; hosts/<env>/packages.nix applies last.
# Keep direction-specific defaults here; per-machine lists stay in user-packages.nix.
{ config, pkgs, lib, ... }:
{
  # Base GNOME look shared by all hosts on this reference (avoid repeating in each user-packages.nix).
  home.packages = with pkgs; [
    kora-icon-theme
    marble-shell-theme
  ];
}
