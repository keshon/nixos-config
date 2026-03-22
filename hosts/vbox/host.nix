# hosts/vbox/host.nix
# Machine-specific settings for 'vbox' (hostname; загрузчик — boot.nix)
{ ... }:

{
  networking.hostName = "nixos-vbox";
}
