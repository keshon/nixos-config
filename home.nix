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
  # Настройки GNOME через dconf
  # ---------------------------------------------------------------------------
  dconf.settings = {
    # DCONF_BEGIN
    "apps/seahorse/listing" = {
      keyrings-selected = [ "gnupg://" ];
    };

    "apps/seahorse/windows/key-manager" = {
      height = 476;
      width = 600;
    };

    "com/mattjakeman/ExtensionManager" = {
      is-maximized = false;
    };

    "org/gnome/Console" = {
      last-window-maximised = false;
      last-window-size = (lib.hm.gvariant.mkTuple [ 1064 722 ]);
    };

    "org/gnome/Music" = {
      window-maximized = false;
    };

    "org/gnome/TextEditor" = {
      last-save-directory = "file:///etc/nixos";
    };

    "org/gnome/baobab/ui" = {
      is-maximized = true;
    };

    "org/gnome/control-center" = {
      last-panel = "keyboard";
      window-state = (lib.hm.gvariant.mkTuple [ 931 614 false ]);
    };

    "org/gnome/desktop/app-folders" = {
      folder-children = [ "System" "Utilities" "YaST" "Pardus" "258278fe-8584-4bac-a3fd-c4ed415087fe" "e8135ad6-1130-4fca-bcd5-a8100deca006" "3f21c19f-0d4c-4477-befc-db6cf7e1353d" ];
    };

    "org/gnome/desktop/app-folders/folders/258278fe-8584-4bac-a3fd-c4ed415087fe" = {
      apps = [ "org.gnome.Calculator.desktop" "org.gnome.Calendar.desktop" "org.gnome.Snapshot.desktop" "org.gnome.clocks.desktop" "org.gnome.Contacts.desktop" "org.gnome.Maps.desktop" "org.gnome.Weather.desktop" ];
      name = "Accessories";
    };

    "org/gnome/desktop/app-folders/folders/3f21c19f-0d4c-4477-befc-db6cf7e1353d" = {
      apps = [ "org.gnome.Yelp.desktop" "nixos-manual.desktop" ];
      name = "Docs";
      translate = false;
    };

    "org/gnome/desktop/app-folders/folders/Pardus" = {
      categories = [ "X-Pardus-Apps" ];
      name = "X-Pardus-Apps.directory";
      translate = true;
    };

    "org/gnome/desktop/app-folders/folders/System" = {
      apps = [ "org.coolercontrol.CoolerControl.desktop" "org.gnome.baobab.desktop" "org.gnome.DiskUtility.desktop" "com.mattjakeman.ExtensionManager.desktop" "org.gnome.Extensions.desktop" "org.gnome.Logs.desktop" "org.gnome.SystemMonitor.desktop" "page.tesk.Refine.desktop" "io.github.flattool.Warehouse.desktop" "xterm.desktop" ];
      name = "X-GNOME-Shell-System.directory";
      translate = true;
    };

    "org/gnome/desktop/app-folders/folders/Utilities" = {
      apps = [ "org.gnome.Characters.desktop" "org.gnome.Connections.desktop" "org.gnome.SimpleScan.desktop" "org.gnome.Papers.desktop" "org.gnome.font-viewer.desktop" "org.gnome.Loupe.desktop" "cups.desktop" "org.gnome.seahorse.Application.desktop" ];
      name = "X-GNOME-Shell-Utilities.directory";
      translate = true;
    };

    "org/gnome/desktop/app-folders/folders/YaST" = {
      categories = [ "X-SuSE-YaST" ];
      name = "suse-yast.directory";
      translate = true;
    };

    "org/gnome/desktop/app-folders/folders/e8135ad6-1130-4fca-bcd5-a8100deca006" = {
      apps = [ "org.gnome.Decibels.desktop" "fr.handbrake.ghb.desktop" "org.bunkus.mkvtoolnix-gui.desktop" "org.gnome.Music.desktop" "org.gnome.Showtime.desktop" "vlc.desktop" ];
      name = "Sound & Video";
    };

    "org/gnome/desktop/background" = {
      color-shading-type = "solid";
      picture-options = "zoom";
      picture-uri = "file:///run/current-system/sw/share/backgrounds/gnome/geometrics-l.jxl";
      picture-uri-dark = "file:///run/current-system/sw/share/backgrounds/gnome/geometrics-d.jxl";
      primary-color = "#26a269";
      secondary-color = "#000000";
    };

    "org/gnome/desktop/input-sources" = {
      mru-sources = [ (lib.hm.gvariant.mkTuple [ "xkb" "us" ]) (lib.hm.gvariant.mkTuple [ "xkb" "ru" ]) ];
      sources = [ (lib.hm.gvariant.mkTuple [ "xkb" "us" ]) (lib.hm.gvariant.mkTuple [ "xkb" "ru" ]) ];
      xkb-options = [ "grp:alt_shift_toggle" ];
    };

    "org/gnome/desktop/interface" = {
      clock-show-seconds = true;
      color-scheme = "default";
      document-font-name = "SF Pro Display 12";
      font-name = "SF Pro Display 11";
      gtk-theme = "Adwaita";
      icon-theme = "kora";
      monospace-font-name = "SF Mono 11";
      toolkit-accessibility = false;
    };

    "org/gnome/desktop/notifications" = {
      application-children = [ "org-gnome-console" "org-gnome-baobab" "org-gnome-nautilus" "gnome-about-panel" "org-gnome-texteditor" "org-gnome-software" "firefox" "io-github-shiftey-desktop" "discord" "v2rayn" ];
    };

    "org/gnome/desktop/notifications/application/discord" = {
      application-id = "discord.desktop";
    };

    "org/gnome/desktop/notifications/application/firefox" = {
      application-id = "firefox.desktop";
    };

    "org/gnome/desktop/notifications/application/gnome-about-panel" = {
      application-id = "gnome-about-panel.desktop";
    };

    "org/gnome/desktop/notifications/application/io-github-shiftey-desktop" = {
      application-id = "io.github.shiftey.Desktop.desktop";
    };

    "org/gnome/desktop/notifications/application/org-gnome-baobab" = {
      application-id = "org.gnome.baobab.desktop";
    };

    "org/gnome/desktop/notifications/application/org-gnome-console" = {
      application-id = "org.gnome.Console.desktop";
    };

    "org/gnome/desktop/notifications/application/org-gnome-nautilus" = {
      application-id = "org.gnome.Nautilus.desktop";
    };

    "org/gnome/desktop/notifications/application/org-gnome-software" = {
      application-id = "org.gnome.Software.desktop";
    };

    "org/gnome/desktop/notifications/application/org-gnome-texteditor" = {
      application-id = "org.gnome.TextEditor.desktop";
    };

    "org/gnome/desktop/notifications/application/v2rayn" = {
      application-id = "v2rayn.desktop";
    };

    "org/gnome/desktop/peripherals/keyboard" = {
      numlock-state = true;
    };

    "org/gnome/desktop/screensaver" = {
      color-shading-type = "solid";
      picture-options = "zoom";
      picture-uri = "file:///run/current-system/sw/share/backgrounds/gnome/geometrics-l.jxl";
      primary-color = "#26a269";
      secondary-color = "#000000";
    };

    "org/gnome/desktop/wm/preferences" = {
      action-middle-click-titlebar = "toggle-maximize";
      button-layout = "appmenu:minimize,maximize,close";
    };

    "org/gnome/evolution-data-server" = {
      migrated = true;
    };

    "org/gnome/gnome-system-monitor" = {
      current-tab = "resources";
      maximized = false;
      show-dependencies = false;
      show-whose-processes = "user";
      window-height = 720;
      window-width = 1141;
    };

    "org/gnome/gnome-system-monitor/proctree" = {
      col-26-visible = false;
      col-26-width = 0;
    };

    "org/gnome/nautilus/preferences" = {
      default-folder-viewer = "icon-view";
      migrated-gtk-settings = true;
    };

    "org/gnome/nautilus/window-state" = {
      initial-size = (lib.hm.gvariant.mkTuple [ 890 550 ]);
      initial-size-file-chooser = (lib.hm.gvariant.mkTuple [ 890 550 ]);
      maximized = false;
    };

    "org/gnome/portal/filechooser/github-desktop" = {
      last-folder-path = "/home/keshon/nixos";
    };

    "org/gnome/portal/filechooser/io.github.shiftey.Desktop" = {
      last-folder-path = "/home/keshon/nixos";
    };

    "org/gnome/portal/filechooser/org.gnome.TextEditor" = {
      last-folder-path = "/etc/nixos";
    };

    "org/gnome/settings-daemon/plugins/color" = {
      night-light-schedule-automatic = false;
    };

    "org/gnome/settings-daemon/plugins/housekeeping" = {
      donation-reminder-last-shown = (lib.hm.gvariant.mkInt64 1773854363479992);
    };

    "org/gnome/shell" = {
      app-picker-layout = [ "{'258278fe-8584-4bac-a3fd-c4ed415087fe': <{'position': <0>}>, '3f21c19f-0d4c-4477-befc-db6cf7e1353d': <{'position': <1>}>, 'e8135ad6-1130-4fca-bcd5-a8100deca006': <{'position': <2>}>, 'System': <{'position': <3>}>, 'Utilities': <{'position': <4>}>, 'discord.desktop': <{'position': <5>}>, 'io.github.shiftey.Desktop.desktop': <{'position': <6>}>, 'org.telegram.desktop.desktop': <{'position': <7>}>, 'tixati.desktop': <{'position': <8>}>, 'v2rayn.desktop': <{'position': <9>}>}" ];
      disabled-extensions = [];
      enabled-extensions = [ "alphabetical-app-grid@stuarthayhurst.com" "appindicatorsupport@rgcjonas.gmail.com" "blur-my-shell@aunetx" "dash-to-dock@micxgx.gmail.com" "desktop-cube@schneegans.github.com" "gsconnect@andyholmes.github.io" "ding@rastersoft.com" "user-theme@gnome-shell-extensions.gcampax.github.com" "AlphabeticalAppGrid@stuarthayhurst" ];
      favorite-apps = [ "firefox.desktop" "org.gnome.TextEditor.desktop" "org.gnome.Nautilus.desktop" "org.gnome.Console.desktop" "org.gnome.Software.desktop" "com.mattjakeman.ExtensionManager.desktop" "org.gnome.tweaks.desktop" "org.gnome.Settings.desktop" ];
      welcome-dialog-last-shown-version = "49.2";
    };

    "org/gnome/shell/extensions/alphabetical-app-grid" = {
      folder-order-position = "start";
    };

    "org/gnome/shell/extensions/blur-my-shell" = {
      pipelines = "{'pipeline_default': {'name': <'Default'>, 'effects': <[<{'type': <'native_static_gaussian_blur'>, 'id': <'effect_000000000000'>, 'params': <{'radius': <30>, 'brightness': <0.59999999999999998>}>}>]>}, 'pipeline_default_rounded': {'name': <'Default rounded'>, 'effects': <[<{'type': <'native_static_gaussian_blur'>, 'id': <'effect_000000000001'>, 'params': <{'radius': <30>, 'brightness': <0.59999999999999998>}>}>, <{'type': <'corner'>, 'id': <'effect_000000000002'>, 'params': <{'radius': <19>}>}>]>}}";
      settings-version = 2;
    };

    "org/gnome/shell/extensions/blur-my-shell/appfolder" = {
      brightness = 0.59999999999999998;
      sigma = 30;
    };

    "org/gnome/shell/extensions/blur-my-shell/coverflow-alt-tab" = {
      pipeline = "pipeline_default";
    };

    "org/gnome/shell/extensions/blur-my-shell/dash-to-dock" = {
      blur = true;
      brightness = 0.59999999999999998;
      pipeline = "pipeline_default_rounded";
      sigma = 30;
      static-blur = true;
      style-dash-to-dock = 0;
    };

    "org/gnome/shell/extensions/blur-my-shell/lockscreen" = {
      pipeline = "pipeline_default";
    };

    "org/gnome/shell/extensions/blur-my-shell/overview" = {
      pipeline = "pipeline_default";
    };

    "org/gnome/shell/extensions/blur-my-shell/panel" = {
      brightness = 0.59999999999999998;
      pipeline = "pipeline_default";
      sigma = 30;
    };

    "org/gnome/shell/extensions/blur-my-shell/screenshot" = {
      pipeline = "pipeline_default";
    };

    "org/gnome/shell/extensions/blur-my-shell/window-list" = {
      brightness = 0.59999999999999998;
      sigma = 30;
    };

    "org/gnome/shell/extensions/dash-to-dock" = {
      autohide = true;
      background-opacity = 0.80000000000000004;
      custom-theme-shrink = true;
      dash-max-icon-size = 48;
      dock-fixed = false;
      dock-position = "BOTTOM";
      extend-height = false;
      height-fraction = 0.90000000000000002;
      intellihide = true;
      preferred-monitor = -2;
      preferred-monitor-by-connector = "Virtual-1";
    };

    "org/gnome/shell/extensions/ding" = {
      check-x11wayland = true;
    };

    "org/gnome/shell/extensions/gsconnect" = {
      missing-openssl = false;
      name = "nixos";
    };

    "org/gnome/shell/extensions/user-theme" = {
      name = "Marble-blue-dark";
    };

    "org/gnome/shell/world-clocks" = {
      locations = [];
    };

    "org/gnome/software" = {
      check-timestamp = (lib.hm.gvariant.mkInt64 1774031902);
      first-run = false;
      flatpak-purge-timestamp = 1773857967;
    };

    "org/gnome/tweaks" = {
      show-extensions-notice = false;
    };

    "org/gtk/gtk4/settings/file-chooser" = {
      show-hidden = false;
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
  nixctl          — центр управления (TUI)

  nixr            — rebuild системы
  nixu            — обновить flake + rebuild
  nixcheck        — dry-run проверка
  nixroll         — откат
  nixgc           — сборка мусора

  nixdconf        — дамп + применить все dconf настройки
  nixdconf-select — дамп + выбор секций (curses TUI)

  nixctl sys rebuild | update | check | gc | rollback
  nixctl pkg search | add | remove | list
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
