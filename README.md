# nixos-config

Personal NixOS / Home Manager configuration.

## nixctl (bundled)

The `nixctl` CLI lives in `./nixctl` and is built by `flake.nix` (no separate repository or flake input).

- `flake.nix` defines the `nixctl` derivation and passes it as `specialArgs` / `home-manager.extraSpecialArgs`.
- Each host’s `hosts/<host>/packages.nix` uses `{ pkgs, nixctl, ... }` and lists `nixctl` in `home.packages`.
- User-installed packages live in `hosts/<host>/user-packages.nix`; `nixctl pkg` edits that file.
- Refresh pinned inputs: `nixctl self bump` (`nix flake lock`), then rebuild when needed.

Ad-hoc from the repo: `nix run ./nixctl -- --help`

## Common workflows

| Goal | Command |
|------|---------|
| Pull latest config | `nixctl self sync` |
| Refresh `flake.lock` | `nixctl self bump` |
| Health / repo info | `nixctl doctor` |
| Check before switch | `nixctl sys check` |

Override config directory: `NIXCTL_DIR=/path/to/repo nixctl …`
