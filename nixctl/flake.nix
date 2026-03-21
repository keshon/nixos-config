{
  description = "nixctl — NixOS control center";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
  let
    system = "x86_64-linux";
    pkgs   = nixpkgs.legacyPackages.${system};

    nixctl = pkgs.stdenvNoCC.mkDerivation {
      pname   = "nixctl";
      version = "0.1.0";
      src     = ./.;

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

      meta = {
        description = "NixOS control center — host, package, dconf and system management";
        homepage    = "https://github.com/keshon/nixctl";
        license     = pkgs.lib.licenses.mit;
        mainProgram = "nixctl";
      };
    };

  in
  {
    # One attrset: Nix forbids two `packages.${system}.…` lines (duplicate dynamic key).
    packages.${system} = {
      default = nixctl;
      # Run tests: nix run .#test
      test = pkgs.writeShellApplication {
        name = "nixctl-test";
        runtimeInputs = [ pkgs.python3 pkgs.python3Packages.pytest ];
        text = ''
          cd ${self}
          pytest tests/ -v
        '';
      };
    };

    # Dev shell: nix develop
    devShells.${system}.default = pkgs.mkShell {
      packages = [
        pkgs.python3
        pkgs.python3Packages.pytest
      ];
      shellHook = ''
        echo "nixctl dev shell"
        echo "  pytest tests/    — run tests"
        echo "  python3 nixctl.py --help"
      '';
    };
  };
}
