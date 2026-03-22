# hosts/desktop/packages.nix — nixctl from flake.nix; list in user-packages.nix
{ pkgs, nixctl, ... }:
let
  userPkgs = import ./user-packages.nix { inherit pkgs; };
in
{
  home.packages = with pkgs; [
    nixctl
  ] ++ userPkgs;
}
