# flake.tmpl.nix — шаблон, управляется через nixctl host
# Не редактировать руками. Для изменения хостов: nixctl host new/remove
{
  description = "NixOS Configuration";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    apple-fonts.url = "github:Lyndeno/apple-fonts.nix";
  };

  outputs = { self, nixpkgs, home-manager, apple-fonts, ... }@inputs:
  let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};

    nixctl = pkgs.stdenvNoCC.mkDerivation {
      pname = "nixctl";
      version = "0.1.0";
      src = ./nixctl;
      nativeBuildInputs = [ pkgs.makeWrapper ];
      installPhase = ''
        mkdir -p $out/lib/nixctl
        cp nixctl.py $out/lib/nixctl/
        cp -r modules $out/lib/nixctl/

        makeWrapper ${pkgs.python3}/bin/python3 $out/bin/nixctl \
          --add-flags "$out/lib/nixctl/nixctl.py" \
          --run 'export NIXCTL_DIR="''${NIXCTL_DIR:-$HOME/nixos}"' \
          --run 'cd "$NIXCTL_DIR" 2>/dev/null || true'
      '';
      meta = with pkgs.lib; {
        description = "NixOS control center — host, package, dconf and system management";
        homepage = "https://github.com/keshon/nixos-config";
        license = licenses.mit;
        mainProgram = "nixctl";
      };
    };

    # env  — окружение (пакеты, host.nix: hostname и пр.)
    # hw   — железо (hardware-configuration.nix, boot.nix — загрузчик этой машины)
    # ref  — референс-профиль: references/<ref>/home.nix между home.nix и packages хоста
    # При обычной работе env == hw.
    # При nixctl host use <other>:
    #   hw  = текущая машина (железо и boot не меняются)
    #   env = выбранное окружение (пакеты и host.nix другого хоста)
    mkHost = { env, hw, ref ? "minimal" }: nixpkgs.lib.nixosSystem {
      inherit system;
      specialArgs = { inherit inputs ref nixctl; };
      modules = [
        ./configuration.nix
        ./hosts/${hw}/hardware-configuration.nix
        ./hosts/${hw}/boot.nix
        ./hosts/${env}/host.nix

        home-manager.nixosModules.home-manager
        {
          home-manager.useGlobalPkgs    = true;
          home-manager.useUserPackages  = true;
          home-manager.extraSpecialArgs = { inherit inputs ref nixctl; };
          home-manager.users.keshon = {
            imports = [
              ./home.nix
              ./references/${ref}/home.nix
              ./hosts/${env}/packages.nix
            ];
          };
        }
      ];
    };

  in
  {
    packages.${system} = {
      inherit nixctl;
      default = nixctl;
    };

    nixosConfigurations = {
__HOSTS__
    };
  };
}
