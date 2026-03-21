# nixctl

NixOS control center. Manage your system, packages, hosts, and GNOME settings from one CLI tool.

```
nixctl sys rebuild            rebuild the system
nixctl pkg search firefox     search and install packages interactively
nixctl host use laptop        switch to another machine's environment
nixctl dconf apply            sync GNOME settings into home.nix
nixctl backup save            snapshot your configs
```

## Installation

**As a flake input** (recommended — single delivery channel; no submodule):

```nix
# flake.nix of your personal nixos config
inputs.nixctl.url = "github:keshon/nixctl";

# hosts/<host>/packages.nix
{ inputs, pkgs, ... }:
let
  userPkgs = import ./user-packages.nix { inherit pkgs; };
in
{
  home.packages = with pkgs; [
    inputs.nixctl.packages.${pkgs.system}.default
  ] ++ userPkgs;
}
```

Update the locked input after upstream changes: `nix flake lock --update-input nixctl` (or `nixctl self bump` from your config repo).

**Run without installing:**
```bash
nix run github:keshon/nixctl -- --help
```

## Configuration

nixctl looks for your NixOS config in `~/nixos/` by default.

Override with an environment variable:
```bash
NIXCTL_DIR=~/my-nixos-config nixctl sys rebuild
```

Your config directory should contain `flake.nix`, `flake.tmpl.nix`, `home.nix`, and `hosts/`.

## Commands

### sys — system management

```bash
nixctl sys rebuild            # nixos-rebuild switch
nixctl sys update             # nix flake update + rebuild
nixctl sys check              # dry-run, no changes applied
nixctl sys rollback           # roll back to previous generation
nixctl sys gc                 # delete old generations (asks confirmation)
nixctl sys generations        # list generation history

nixctl sys rebuild --host laptop   # override target host
```

### host — multi-machine management

```bash
nixctl host list              # all hosts, active marked ★
nixctl host new laptop        # create hosts/laptop/ + update flake.nix
nixctl host use laptop        # switch active environment
nixctl host remove laptop     # remove host (asks confirmation)
nixctl host info [laptop]     # show host status
```

**How host switching works:**

nixctl separates *environment* (`env`) from *hardware* (`hw`).
When you run `nixctl host use laptop` on your desktop:

- Hardware stays from `desktop` (`hardware-configuration.nix`)
- Packages and settings come from `laptop` (`packages.nix`, `host.nix`)

This lets you inspect and edit any machine's config from any other machine safely.
`nixctl sys rebuild` will warn you if `env ≠ machine` before applying.

The `flake.nix` is generated from `flake.tmpl.nix` — do not edit it directly.

### pkg — package management

```bash
nixctl pkg search firefox           # search (local cache first, then network)
nixctl pkg search firefox --fresh   # force network search
nixctl pkg add vlc                  # add to packages.nix (asks which machine)
nixctl pkg remove vlc               # remove from packages.nix
nixctl pkg list                     # list installed packages
```

User-selected packages are stored in `hosts/<host>/user-packages.nix` (and `packages.nix` pulls in nixctl from the flake). Legacy layouts with only `packages.nix` still work.
`pkg add` asks whether to install for this machine only, another machine, or all machines.

### dconf — GNOME settings

```bash
nixctl dconf apply            # dump dconf + insert all sections into home.nix
nixctl dconf apply --select   # same, with interactive curses section picker
nixctl dconf dump             # only save to dconf-backup.txt
```

Settings are inserted between markers in `home.nix`:

```nix
dconf.settings = {
  # DCONF_BEGIN
  # (managed by nixctl dconf apply)
  # DCONF_END
};
```

### self — repo sync and flake input

```bash
nixctl self status    # short git summary
nixctl self sync      # git pull --rebase (config repo only)
nixctl self bump      # nix flake lock --update-input nixctl
nixctl self push      # commit and push
```

`self pull` and `self update` are aliases for `sync` and `bump` respectively.

### doctor — delivery check

```bash
nixctl doctor         # flake.lock nixctl rev, NIXCTL_DIR, optional legacy nixctl/
```

### backup — config snapshots

```bash
nixctl backup save            # snapshot to backups/<timestamp>/
nixctl backup list            # list snapshots
nixctl backup restore         # restore latest snapshot
nixctl backup restore 3       # restore third snapshot by number
```

Snapshots are stored in `backups/` (gitignored). Last 10 are kept automatically.

### cache — offline installation

```bash
nixctl cache export /mnt/usb/nix-cache   # copy system closure to USB drive
nixctl cache import /mnt/usb/nix-cache   # rebuild using local cache (no internet)
```

### bootstrap — first-time setup

```bash
nixctl bootstrap
```

Interactive wizard for a fresh machine:
1. Detect host from `flake.nixosConfigurations` (or ask)
2. Copy `hardware-configuration.nix` → `hosts/<host>/`
3. `git add` the hardware config so Nix flakes can see it
4. Create symlink `/etc/nixos → ~/nixos`
5. `nixos-rebuild switch`
6. Add Flathub

**One-liner for a fresh NixOS install:**
```bash
nix-shell -p git --run "git clone https://github.com/keshon/nixos-config ~/nixos" && \
bash ~/nixos/bootstrap.sh
```

## Repository structure

```
nixctl/                        ← this repo (public)
  nixctl.py                    # entry point
  modules/
    config.py                  # paths, store, host detection
    sys.py                     # system commands
    host.py                    # host management, flake generation
    pkg.py                     # package management
    dconf.py                   # GNOME settings
    backup.py                  # snapshots
    cache.py                   # offline cache
    bootstrap.py               # first-time setup
  tests/
  flake.nix                    # makes nixctl a Nix package

your-nixos-config/             ← your personal repo (private)
  flake.nix                    # generated from flake.tmpl.nix
  flake.tmpl.nix               # template — edit this, not flake.nix
  flake.lock
  home.nix                     # shared user environment
  configuration.nix            # shared system config
  hosts/
    desktop/
      host.nix                 # hostname, bootloader
      packages.nix             # packages for this machine
      hardware-configuration.nix
    laptop/
      host.nix
      packages.nix              # imports nixctl + user-packages.nix
      user-packages.nix         # list edited by nixctl pkg
      hardware-configuration.nix
  backups/                     # gitignored
  .nixctl-store                # gitignored (active host, machine identity)
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
