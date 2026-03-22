# nixos-config

Personal NixOS / Home Manager configuration.

## nixctl (bundled)

The `nixctl` CLI lives in `./nixctl` and is built by `flake.nix` (no separate repository or flake input).

- `flake.nix` defines the `nixctl` derivation and passes it as `specialArgs` / `home-manager.extraSpecialArgs`.
- Each host’s `hosts/<host>/packages.nix` uses `{ pkgs, nixctl, ... }` and lists `nixctl` in `home.packages`.
- User-installed packages live in `hosts/<host>/user-packages.nix`; `nixctl pkg` edits that file.
- Refresh pinned inputs: `nixctl git bump` (`nix flake lock`), then rebuild when needed.

Ad-hoc from the repo: `nix run ./nixctl -- --help`

## Common workflows

| Goal | Command |
|------|---------|
| Pull latest config | `nixctl git sync` |
| Refresh `flake.lock` | `nixctl git bump` |
| Check before switch | `nixctl sys check` |

Override config directory: `NIXCTL_DIR=/path/to/repo nixctl …`

`nixctl git push` uses `git push` — GitHub still requires authentication to push, even for a public repo (SSH or HTTPS with a [personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens), not your account password). `nixctl git status`, `sync`, and `bump` avoid interactive credential prompts for read-only operations.

The `nixctl self …` name is an alias for `nixctl git …`.
