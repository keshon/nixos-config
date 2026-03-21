# hosts/laptop/host.nix
# Настройки профиля машины 'laptop' (hostname; загрузчик — boot.nix)
{ ... }:

{
  networking.hostName = "nixos-laptop";
}
