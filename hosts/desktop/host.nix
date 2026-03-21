# hosts/desktop/host.nix
# Machine-specific settings for 'desktop' (hostname, сеть и т.д.; загрузчик — boot.nix)
{ ... }:

{
  networking.hostName = "nixos-desktop";
}
