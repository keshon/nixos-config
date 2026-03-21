# hosts/desktop/packages.nix
{ pkgs, ... }:

{
  home.packages = with pkgs; [
    firefox
    vlc
    discord
    telegram-desktop

    # nixctl
    (writeShellScriptBin "nixctl" ''
      cd "$HOME/nixos" && exec ${pkgs.python3}/bin/python3 "$HOME/nixos/nixctl.py" "$@"
    '')
  ];
}
