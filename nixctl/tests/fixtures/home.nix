{ config, pkgs, lib, inputs, ... }:

{
  home.username = "testuser";
  home.homeDirectory = "/home/testuser";
  home.stateVersion = "25.11";

  dconf.settings = {
    # DCONF_BEGIN
    # DCONF_END
  };

  programs.home-manager.enable = true;
}
