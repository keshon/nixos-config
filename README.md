# nixos-config

Personal NixOS / Home Manager configuration.

## nixctl delivery (happy path)

Use **one** channel for the `nixctl` CLI: the **flake input** `nixctl` (see `flake.nix` / `flake.lock`), not a git submodule and not a separate checkout wired with `writeShellScriptBin`.

- Declare `inputs.nixctl.url = "github:keshon/nixctl";` in your flake.
- In each host’s `packages.nix`, add `inputs.nixctl.packages.${pkgs.system}.default` to `home.packages` (see `hosts/*/packages.nix`).
- User-installed packages live in `hosts/<host>/user-packages.nix`; `nixctl pkg` edits that file.
- Update the tool: `nixctl self bump` (updates the locked input), then rebuild.

Ad-hoc use without installing: `nix run github:keshon/nixctl -- <args>` (optional).

## Common workflows

| Goal | Command |
|------|---------|
| Pull latest config | `nixctl self sync` |
| Bump nixctl input | `nixctl self bump` |
| Health / lock info | `nixctl doctor` |
| Check before switch | `nixctl sys check` |

Override config directory: `NIXCTL_DIR=/path/to/repo nixctl …`
