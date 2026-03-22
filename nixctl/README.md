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

In **keshon/nixos-config**, nixctl ships inside this repository: `./nixctl` is built by the top-level `flake.nix` and passed into Home Manager as `nixctl` (see `specialArgs` / `extraSpecialArgs`).

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

Refresh pinned inputs for the whole flake: `nixctl git bump` (runs `nix flake lock`). Same as `nixctl self bump` (alias).

**Run without installing into the profile:**
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

## Commands

### sys — system management

```bash
nixctl sys rebuild            # nixos-rebuild switch
nixctl sys update             # nix flake update + rebuild
nixctl sys check              # dry-run, no changes applied
nixctl sys rollback           # roll back to previous generation
nixctl sys gc                 # delete old generations (asks confirmation)
nixctl sys generations        # list generation history

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

User-selected packages are stored in `hosts/<host>/user-packages.nix` (and `packages.nix` pulls in nixctl from `flake.nix`). Legacy layouts with only `packages.nix` still work.
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

### git — repo sync and flake lock

```bash
nixctl git status     # short git summary
nixctl git sync       # git pull --rebase (config repo only)
nixctl git bump       # nix flake lock (refresh pinned inputs)
nixctl git push       # commit and push
```

`nixctl self …` is an alias for `nixctl git …`. Subcommands `pull` and `update` are aliases for `sync` and `bump`.

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
nixctl bootstrap --resume [HOST]    # skip wizard; continue from hardware → rebuild
nixctl bootstrap --resume --force-hardware [HOST]   # re-copy hardware from /etc/nixos
```

Interactive wizard for a fresh machine:
1. Detect host from `flake.nixosConfigurations` (or ask)
2. Copy `hardware-configuration.nix` → `hosts/<host>/`
3. `git add` the hardware config so Nix flakes can see it
4. Create symlink `/etc/nixos → ~/nixos`
5. `nixos-rebuild switch`
6. Add Flathub

If something fails (often step 5), fix `flake.nix` / `hosts/…` and run **`nixctl bootstrap --resume vbox`** (or omit the name if `.nixctl-store` already has the host). Hardware copy is skipped when `hosts/<host>/hardware-configuration.nix` already exists unless you pass **`--force-hardware`**.

**One-liner for a fresh NixOS install:**
```bash
nix-shell -p git --run "git clone https://github.com/keshon/nixos-config ~/nixos" && \
bash ~/nixos/bootstrap.sh
```

## Repository structure (nixos-config)

```
nixos-config/
  flake.nix                    # defines nixctl + nixosConfigurations
  flake.tmpl.nix               # template for nixctl host new — do not edit flake.nix by hand
  nixctl/                      # nixctl CLI (this subtree)
    nixctl.py
    modules/
    tests/
    flake.nix                  # optional: nix develop / nix run ./nixctl
  home.nix
  configuration.nix
  hosts/
    <host>/packages.nix        # nixctl + user-packages.nix
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
