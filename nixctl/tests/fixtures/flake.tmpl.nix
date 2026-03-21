{
  description = "NixOS Configuration";
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  outputs = { self, nixpkgs, ... }@inputs:
  let
    system = "x86_64-linux";
    mkHost = { env, hw, ref ? "minimal" }: nixpkgs.lib.nixosSystem {
      inherit system;
      modules = [
        ./hosts/${hw}/hardware-configuration.nix
        ./hosts/${hw}/boot.nix
        ./hosts/${env}/host.nix
      ];
    };
  in
  {
    nixosConfigurations = {
__HOSTS__
    };
  };
}
