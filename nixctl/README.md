# nixctl

NixOS configuration helper: system rebuilds, packages, flake machines/profiles, GNOME settings, git, backups, and cache — from one CLI.

Every command prints a one-line context on stderr, for example:

`nixctl | machine=vbox | profile=desktop | /home/you/nixos#vbox`

Run `nixctl` with no arguments for a short list of groups; `nixctl --help` for the full command reference.

```
nixctl sys rebuild
nixctl pkg search firefox
nixctl host use laptop
nixctl dconf apply
nixctl backup save
```

## Quick start (fresh NixOS install)

Clone this repo into `~/nixos` and run the root `bootstrap.sh` (it invokes `nixctl bootstrap` via `nix run` when flakes are available):

```bash
nix-shell -p git --run "git clone https://github.com/keshon/nixos-config ~/nixos" && \
bash ~/nixos/bootstrap.sh
```

Requires `nix` with flakes enabled for the scripted path; see `bootstrap.sh` in the repo for `--resume` and fallbacks.

## Installation

In **keshon/nixos-config**, nixctl lives in `./nixctl` and is built by the top-level `flake.nix`, then passed into Home Manager as `nixctl` (see `specialArgs` / `extraSpecialArgs`).

```nix
# hosts/<host>/packages.nix
{ pkgs, nixctl, ... }:
let
  userPkgs = import ./user-packages.nix { inherit pkgs; };
in
{
  home.packages = with pkgs; [
    nixctl
  ] ++ userPkgs;
}
```

Refresh pinned inputs for the whole flake: `nixctl git bump` (same as `nixctl self bump`).

**Run without installing into the profile** (from the repo root):

```bash
nix run ./nixctl -- --help
```

## Configuration

nixctl looks for your NixOS config in `~/nixos/` by default.

Override with an environment variable:

```bash
NIXCTL_DIR=~/my-nixos-config nixctl sys rebuild
```

Your config directory should contain `flake.nix`, `flake.tmpl.nix`, `home.nix`, and `hosts/`.

### Bootloader (UEFI vs BIOS)

If you picked GRUB for a UEFI machine and the system will not boot, you do not need a new flake host: edit `hosts/<hardware>/boot.nix` to use systemd-boot, or from the repo run:

```bash
bash scripts/set-boot-uefi.sh [HOST]
sudo nixos-rebuild switch --flake ~/nixos#HOST
```

`nixctl host new` and bootstrap default to **UEFI** when `/sys/firmware/efi` exists.

### GNOME and Home Manager

Every key under `dconf.settings` in `home.nix` is re-applied on each `home-manager switch`, overwriting the same keys in your session. Keep that block small for things you want enforced (e.g. keyboard layout); leave dock, extensions, favorites, and window sizes to **GNOME Settings** — or use `nixctl dconf apply` once and merge only what you want to keep declaratively.

### Verifying package edits

After `nixctl pkg add` or search install, nixctl runs `nix build` on the current machine’s system closure (no switch). If it fails, fix the list or network and run `nixctl pkg verify` again. To skip the automatic check: `NIXCTL_SKIP_VERIFY=1 nixctl pkg add …`.

## Commands

### sys — system management

```bash
nixctl sys rebuild
nixctl sys update              # nix flake update + rebuild
nixctl sys check               # dry-run
nixctl sys rollback
nixctl sys gc                  # delete old generations (asks confirmation)
nixctl sys generations
```

If your **software profile** (flake `env`) differs from **this machine’s** flake name, `nixctl sys rebuild` warns before applying.

### host — flake entries, profiles, and hardware

```bash
nixctl host list               # table: FLAKE, PROFILE, HARDWARE, ref, HW-CONF
nixctl host new laptop         # create hosts/laptop/ + update flake.nix
nixctl host use laptop         # point this machine’s profile at another flake name (advanced)
nixctl host remove laptop      # remove entry (asks confirmation)
nixctl host info [laptop]      # paths and files for one flake name
```

**Profile vs hardware:** the flake defines `env` (software under `hosts/<env>/`) and `hw` (disks/boot under `hosts/<hw>/`). `nixctl host use laptop` on another machine keeps **hardware** on the current machine and borrows **packages/host.nix** from the `laptop` profile. `nixctl sys rebuild` warns when profile and machine name differ.

`flake.nix` is generated from `flake.tmpl.nix` — do not edit `flake.nix` by hand; use `nixctl host` commands.

### pkg — package management

```bash
nixctl pkg search firefox
nixctl pkg search firefox --fresh
nixctl pkg add vlc
nixctl pkg remove vlc
nixctl pkg list
nixctl pkg verify
```

User packages live in `hosts/<profile>/user-packages.nix` when present. `pkg add` asks: this machine, another flake entry, or shared `home.nix`. After adding packages, nixctl runs a **nix build** (no activation) unless `NIXCTL_SKIP_VERIFY=1`.

### dconf — GNOME settings

```bash
nixctl dconf apply
nixctl dconf apply --select
nixctl dconf dump
```

Settings are inserted between markers in `home.nix`:

```nix
dconf.settings = {
  # DCONF_BEGIN
  # (managed by nixctl dconf apply)
  # DCONF_END
};
```

### git — repo sync and flake lock

```bash
nixctl git status
nixctl git sync
nixctl git bump
nixctl git push
```

`nixctl self …` is an alias for `nixctl git …`. Subcommands `pull` and `update` alias `sync` and `bump`.

### backup — config snapshots

```bash
nixctl backup save
nixctl backup list
nixctl backup restore
nixctl backup restore 3
```

Snapshots live under `backups/` (gitignored). The last 10 are kept automatically.

### cache — offline installation

```bash
nixctl cache export /mnt/usb/nix-cache
nixctl cache import /mnt/usb/nix-cache
```

### bootstrap — first-time setup

Same flow as [Quick start](#quick-start), or run manually after cloning:

```bash
nixctl bootstrap
nixctl bootstrap --resume [HOST]
nixctl bootstrap --resume --force-hardware [HOST]
```

Interactive steps: pick or create a flake host, copy `hardware-configuration.nix`, symlink `/etc/nixos` → `~/nixos`, `nixos-rebuild switch`, Flathub. If step fails, fix the config and run `nixctl bootstrap --resume` (host name optional if `.nixctl-store` is set). Use `--force-hardware` to re-copy hardware from `/etc/nixos`.

## Repository structure (nixos-config)

```
nixos-config/
  bootstrap.sh                 # quick start entry (nix run nixctl bootstrap)
  scripts/set-boot-uefi.sh     # rewrite boot.nix to UEFI if you chose GRUB by mistake
  flake.nix                    # defines nixctl + nixosConfigurations
  flake.tmpl.nix               # template for nixctl host new
  nixctl/                      # nixctl CLI (this subtree)
    nixctl.py
    modules/
    tests/
    flake.nix                  # nix develop / nix run ./nixctl
  home.nix
  configuration.nix
  hosts/
    <host>/packages.nix
    <host>/user-packages.nix
  backups/                     # gitignored
  .nixctl-store                # gitignored
```

## Running tests

```bash
# With nix dev shell
nix develop
pytest tests/ -v

# Without nix
python3 -m pytest tests/ -v
```

## License

MIT
