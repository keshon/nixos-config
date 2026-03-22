# references/minimal/home.nix — Home Manager fragment for reference profile "minimal".
# Inherits after repo-wide home.nix; hosts/<env>/packages.nix applies last.
# Keep direction-specific defaults here; per-machine lists stay in user-packages.nix.
{ config, pkgs, lib, ... }:
{
  # Intentionally minimal — add shared options for this profile when needed.
  kora-icon-theme
  marble-shell-theme
}
