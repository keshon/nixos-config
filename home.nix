{ config, pkgs, lib, inputs, ... }:

let
  vraynBinDir = "v2rayN/bin"; # структура, где vrayn ищет бинарь и данные
in
{
  # Пакеты подключаются из hosts/<host>/packages.nix через flake.nix
  # Список пакетов: hosts/<host>/user-packages.nix (nixctl pkg add/remove)

  home.username = "keshon";
  home.homeDirectory = "/home/keshon";
  home.stateVersion = "25.11";


  # ---------------------------------------------------------------------------
  # Симлинки и данные для VRAYN
  # ---------------------------------------------------------------------------
  xdg.dataFile = {
    # бинарь xray для vrayn
    "${vraynBinDir}/xray/xray".source = "${pkgs.xray}/bin/xray";

    # geoip и geosite
    "${vraynBinDir}/geoip.dat".source    = "${pkgs.v2ray-geoip}/share/v2ray/geoip.dat";
    "${vraynBinDir}/geosite.dat".source  = "${pkgs.v2ray-domain-list-community}/share/v2ray/geosite.dat";
  };

  # ---------------------------------------------------------------------------
  # GNOME / dconf — keep this SMALL. Every key here is re-applied on each
  # `home-manager switch` and overwrites the same keys in the live session.
  # Dock, extensions, favorites, window sizes, etc. belong in GNOME Settings,
  # not here. Use `nixctl dconf apply` to capture a dump once; merge only what
  # you want enforced forever. Markers are for nixctl dconf apply injection.
  # ---------------------------------------------------------------------------
  dconf.settings = {
    # DCONF_BEGIN
    "org/gnome/desktop/input-sources" = {
      mru-sources = [ (lib.hm.gvariant.mkTuple [ "xkb" "us" ]) (lib.hm.gvariant.mkTuple [ "xkb" "ru" ]) ];
      sources = [ (lib.hm.gvariant.mkTuple [ "xkb" "us" ]) (lib.hm.gvariant.mkTuple [ "xkb" "ru" ]) ];
      xkb-options = [ "grp:alt_shift_toggle" ];
    };

    "org/gnome/desktop/peripherals/keyboard" = {
      numlock-state = true;
    };
    # DCONF_END
  };

  # ---------------------------------------------------------------------------
  # Git
  # ---------------------------------------------------------------------------
  programs.git = {
    enable   = true;
    settings = {
      user.name          = "keshon";
      user.email         = "keshon@zoho.com";
      init.defaultBranch = "main";
      pull.rebase        = true;
    };
  };

  # ---------------------------------------------------------------------------
  # Bash
  # ---------------------------------------------------------------------------
  programs.bash = {
    enable = true;
    shellAliases = {
      ll      = "ls -la";
      nixcd   = "cd ~/nixos";
      nixconf = "gnome-text-editor ~/nixos/configuration.nix ~/nixos/home.nix ~/nixos/flake.nix &";
      nixcheck = "sudo nixos-rebuild dry-activate --flake ~/nixos#desktop";
      nixr     = "sudo nixos-rebuild switch --flake ~/nixos#desktop";
      nixu     = "nix flake update && sudo nixos-rebuild switch --flake ~/nixos#desktop";
      nixroll  = "sudo nixos-rebuild switch --rollback";
      nixgc    = "sudo nix-collect-garbage -d";
      nixlog   = "nixos-rebuild list-generations";
      nixdconf = "nixctl dconf apply";
      nixdconf-select = "nixctl dconf apply --select";
      nixhelp  = ''echo "
  nixctl          — control center (TUI)

  nixr            — rebuild system
  nixu            — flake update + rebuild
  nixcheck        — dry-run
  nixroll         — rollback
  nixgc           — garbage-collect

  nixdconf        — dump dconf + merge into home.nix
  nixdconf-select — dump + pick sections (curses)

  nixctl sys rebuild | update | check | gc | rollback
  nixctl pkg search | add | remove | list | verify
  nixctl git sync | bump | push | status
  nixctl dconf apply [--select]
  nixctl backup save | list | restore
  nixctl cache export/import <path>
  nixctl bootstrap [--resume]
"'';
    };
  };

  # ---------------------------------------------------------------------------
  # Разрешить Home Manager управлять собой
  # ---------------------------------------------------------------------------
  programs.home-manager.enable = true;
}
