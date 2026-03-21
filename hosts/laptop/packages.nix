# hosts/laptop/packages.nix — nixctl from flake; list in user-packages.nix
{ pkgs, inputs, ... }:
let
  userPkgs = import ./user-packages.nix { inherit pkgs; };
in
{
  home.packages = with pkgs; [
    inputs.nixctl.packages.${pkgs.system}.default
  ] ++ userPkgs;
}
