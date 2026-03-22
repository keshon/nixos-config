# hosts/vbox/boot.nix — загрузчик (в flake импортируется только с hw)
{ ... }:

{
  # Legacy BIOS + GRUB
  boot.loader.grub.enable      = true;
  boot.loader.grub.useOSProber = true;
  boot.loader.grub.device      = "/dev/sda";
}
