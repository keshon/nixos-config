# hosts/laptop/boot.nix — загрузчик этой машины (в flake импортируется только с hw)
{ ... }:

{
  # UEFI
  boot.loader.systemd-boot.enable      = true;
  boot.loader.efi.canTouchEfiVariables = true;
}
