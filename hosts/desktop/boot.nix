# hosts/desktop/boot.nix — загрузчик этой машины (в flake импортируется только с hw)
{ ... }:

{
  # Legacy BIOS + GRUB (VirtualBox)
  boot.loader.grub = {
    enable      = true;
    device      = "/dev/sda";
    useOSProber = true;
  };
}
