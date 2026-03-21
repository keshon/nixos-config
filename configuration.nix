# configuration.nix
# Общий системный конфиг для всех машин.
# Специфика машины: hostname — hosts/<host>/host.nix; загрузчик — hosts/<host>/boot.nix
# Пакеты пользователя — в hosts/<host>/packages.nix
{ config, pkgs, inputs, ... }:

{
  # ---------------------------------------------------------------------------
  # Временная зона и локаль
  # ---------------------------------------------------------------------------
  time.timeZone = "Europe/Moscow";

  i18n.defaultLocale = "en_US.UTF-8";
  i18n.extraLocaleSettings = {
    LC_ADDRESS        = "ru_RU.UTF-8";
    LC_IDENTIFICATION = "ru_RU.UTF-8";
    LC_MEASUREMENT    = "ru_RU.UTF-8";
    LC_MONETARY       = "ru_RU.UTF-8";
    LC_NAME           = "ru_RU.UTF-8";
    LC_NUMERIC        = "ru_RU.UTF-8";
    LC_PAPER          = "ru_RU.UTF-8";
    LC_TELEPHONE      = "ru_RU.UTF-8";
    LC_TIME           = "ru_RU.UTF-8";
  };

  # ---------------------------------------------------------------------------
  # Загрузчик — общее
  # ---------------------------------------------------------------------------
  # Тема GRUB — применяется только для BIOS хостов (grub.enable = true).
  # Для UEFI хостов (systemd-boot) Nix игнорирует эту настройку автоматически.
  boot.loader.grub.theme = pkgs.stdenv.mkDerivation {
    pname   = "distro-grub-themes";
    version = "3.1";
    src = pkgs.fetchFromGitHub {
      owner = "AdisonCavani";
      repo  = "distro-grub-themes";
      rev   = "v3.1";
      hash  = "sha256-ZcoGbbOMDDwjLhsvs77C7G7vINQnprdfI37a9ccrmPs=";
    };
    installPhase = "cp -r customize/nixos $out";
  };

  # ---------------------------------------------------------------------------
  # Сеть
  # ---------------------------------------------------------------------------
  networking.networkmanager.enable = true;

  # ---------------------------------------------------------------------------
  # Рабочий стол (GNOME + Wayland)
  # ---------------------------------------------------------------------------
  services.xserver.enable               = true;
  services.displayManager.gdm.enable    = true;
  services.desktopManager.gnome.enable  = true;

  programs.dconf.enable = true;

  services.desktopManager.gnome.extraGSettingsOverrides = ''
    [org.gnome.mutter]
    experimental-features=['scale-monitor-framebuffer', 'xwayland-native-scaling']
  '';

  environment.gnome.excludePackages = with pkgs; [
    gnome-tour
    cheese
    epiphany
  ];

  # ---------------------------------------------------------------------------
  # Звук (PipeWire)
  # ---------------------------------------------------------------------------
  services.pulseaudio.enable = false;
  security.rtkit.enable      = true;
  services.pipewire = {
    enable            = true;
    alsa.enable       = true;
    alsa.support32Bit = true;
    pulse.enable      = true;
  };

  # ---------------------------------------------------------------------------
  # Принтеры
  # ---------------------------------------------------------------------------
  services.printing.enable = true;

  # ---------------------------------------------------------------------------
  # Flatpak
  # ---------------------------------------------------------------------------
  services.flatpak.enable = true;
  # Важно: добавить flathub вручную после установки:
  # flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

  # ---------------------------------------------------------------------------
  # Пользователи
  # ---------------------------------------------------------------------------
  users.users.keshon = {
    isNormalUser = true;
    description  = "keshon";
    extraGroups  = [ "wheel" "networkmanager" ];
  };

  # ---------------------------------------------------------------------------
  # Системные программы и пакеты
  # ---------------------------------------------------------------------------
  programs.firefox.enable         = true;
  programs.coolercontrol.enable   = true;

  environment.systemPackages = with pkgs; [
    mc
    wget
    gnome-tweaks
    gnome-extension-manager

    # GNOME Extensions
    gnomeExtensions.alphabetical-app-grid
    gnomeExtensions.appindicator
    gnomeExtensions.blur-my-shell
    gnomeExtensions.dash-to-dock
    gnomeExtensions.desktop-cube
    gnomeExtensions.gsconnect
    gnomeExtensions.desktop-icons-ng-ding
    gnomeExtensions.user-themes
  ];

  # ---------------------------------------------------------------------------
  # Шрифты
  # ---------------------------------------------------------------------------
  fonts = {
    enableDefaultPackages = true;
    packages = [
      inputs.apple-fonts.packages.${pkgs.system}.sf-pro
      inputs.apple-fonts.packages.${pkgs.system}.sf-mono
      inputs.apple-fonts.packages.${pkgs.system}.ny
    ];
    fontconfig.defaultFonts = {
      sansSerif = [ "SF Pro Display" ];
      monospace = [ "SF Mono" ];
    };
  };

  # ---------------------------------------------------------------------------
  # Nix
  # ---------------------------------------------------------------------------
  nixpkgs.config.allowUnfree = true;

  nix.settings = {
    experimental-features = [ "nix-command" "flakes" ];
    auto-optimise-store   = true;
  };

  nix.gc = {
    automatic = true;
    dates     = "weekly";
    options   = "--delete-older-than 7d";
  };

  # ---------------------------------------------------------------------------
  # Системная версия
  # ---------------------------------------------------------------------------
  system.stateVersion = "25.11";
}
