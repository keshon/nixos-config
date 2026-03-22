"""
modules/bootstrap.py — first-time setup on a new machine

nixctl bootstrap
"""

import os
import shutil
import platform
import datetime

from .config import (
    NIXOS_DIR, HOSTS_DIR, exec_shell, flake_target,
    confirm, _hosts_from_flake,
    save_store, load_store,
    REFERENCES_DIR, REFERENCE_DEFAULT,
)
from .host import (
    create_host_files,
    validate_new_host,
    _ask_bootloader,
    _print_boot_plan,
)
from .reference import discover_references

HELP = """\
nixctl bootstrap

  First-time NixOS setup on a new machine.
  Run once after cloning this repo.

  You will either attach this PC to an existing host in flake.nix or
  create a new host entry (name + reference template), then hardware copy,
  /etc/nixos symlink, rebuild, and Flathub.

  nixctl bootstrap --resume [HOST]

  Skip the wizard and continue from hardware -> symlink -> rebuild -> store -> Flathub.
  Use after fixing a failed step (e.g. nixos-rebuild error). HOST defaults to
  .nixctl-store or hostname hint.

  nixctl bootstrap --resume --force-hardware [HOST]

  Same as --resume but always re-copy hardware-configuration.nix from /etc/nixos.
"""


def _parse_bootstrap_args(args: list) -> tuple[list, bool, bool]:
    """Return (positional_args, resume, force_hardware)."""
    resume = False
    force_hw = False
    pos: list[str] = []
    for a in args:
        if a in ("--resume", "-r"):
            resume = True
        elif a == "--force-hardware":
            force_hw = True
        else:
            pos.append(a)
    return pos, resume, force_hw


def run(args: list):
    if any(a in ("-h", "--help") for a in args):
        print(HELP)
        return

    pos, resume, force_hw = _parse_bootstrap_args(args)
    if resume:
        _resume_bootstrap(pos, force_hw=force_hw)
        return

    print("nixctl bootstrap")
    print("-" * 40)
    _print_intro()

    mode = _choose_mode()
    if mode is None:
        print("  Cancelled.")
        return

    if mode == "existing":
        host = _pick_existing_host()
    else:
        host = _bootstrap_new_from_ref()

    if not host:
        print("  Cancelled.")
        return

    print(f"\n  Host: {host}\n")

    if not _finalize_bootstrap(host, resume=False, force_hw=False):
        return

    print()
    print("done: bootstrap finished.")
    print("  Log out and back in for GNOME settings to apply.")


def _resume_bootstrap(pos: list, *, force_hw: bool = False):
    """Wizard skipped: run finalize steps only (idempotent where possible)."""
    print("nixctl bootstrap --resume")
    print("-" * 40)
    host = pos[0].strip() if pos else ""
    if not host:
        st = load_store()
        host = (st.get("host") or st.get("machine") or "").strip()
    if not host:
        import platform
        hint = platform.node().lower().split(".")[0]
        print(f"  No host in .nixctl-store; hostname hint: {hint}")
        host = input("  Host name (must match flake.nix nixosConfigurations): ").strip()
    if not host:
        print("  error: host name required")
        return

    print()
    print(f"  Host: {host}")
    print("  (skipping wizard — hardware copy unless already present, then symlink, rebuild, …)")
    print()

    if not _finalize_bootstrap(host, resume=True, force_hw=force_hw):
        return

    print()
    print("done: bootstrap finished.")
    print("  Log out and back in for GNOME settings to apply.")


def _print_intro():
    print()
    print(
        "  This wizard either attaches this machine to a host that already exists "
        "in the flake, or creates a new host from a reference template "
        "(references/<ref>/home.nix), then applies hardware and rebuilds."
    )
    print()


def _choose_mode() -> str | None:
    print("  [1] Use an existing host from this repo (flake.nix)")
    print("  [2] Create a new host from a reference template")
    for _ in range(5):
        ans = input("  Choice [1]: ").strip()
        if not ans or ans == "1":
            return "existing"
        if ans == "2":
            return "new"
        print("  Invalid choice (use 1 or 2).")
    print("  Too many invalid attempts.")
    return None


def _pick_existing_host() -> str | None:
    detected = platform.node().lower().split(".")[0]
    hosts = _hosts_from_flake()

    if not hosts:
        print(f"  Hostname: {detected}")
        print("  No flake hosts found (nix eval failed or empty).")
        ans = input("  Enter flake host name manually: ").strip()
        return ans or None

    print(f"  Hostname: {detected}")
    print(f"  Flake hosts: {', '.join(hosts)}")
    print()

    auto_match = None
    for h in hosts:
        if h == detected or h in detected or detected in h:
            auto_match = h
            break

    if auto_match:
        print(f"  Suggested match: {auto_match}")

    for i, h in enumerate(hosts, 1):
        marker = " (suggested)" if h == auto_match else ""
        print(f"    [{i}] {h}{marker}")

    default = hosts.index(auto_match) + 1 if auto_match else 1
    ans = input(f"  Choose host [{default}]: ").strip()

    try:
        idx = int(ans) - 1 if ans else default - 1
        if 0 <= idx < len(hosts):
            return hosts[idx]
    except ValueError:
        if ans in hosts:
            return ans

    print("  error: invalid choice.")
    return None


def _resolve_reference_list() -> list[str] | None:
    """Return list of ref names, or None if none available."""
    refs = discover_references()
    if refs:
        return refs
    fallback = os.path.join(REFERENCES_DIR, REFERENCE_DEFAULT, "home.nix")
    if os.path.isfile(fallback):
        print(
            f"  No references/*/home.nix found; using default "
            f"\"{REFERENCE_DEFAULT}\" ({fallback})."
        )
        return [REFERENCE_DEFAULT]
    print(f"  error: no reference profiles found under {REFERENCES_DIR}")
    print("    Add references/<name>/home.nix, then re-run bootstrap.")
    return None


def _bootstrap_new_from_ref() -> str | None:
    refs = _resolve_reference_list()
    if not refs:
        return None

    print()
    print("  Reference templates:")
    for i, r in enumerate(refs, 1):
        mark = " (default)" if r == REFERENCE_DEFAULT else ""
        print(f"    [{i}] {r}{mark}")

    default_ref = 1
    ans = input(f"  Choose template [{default_ref}]: ").strip()
    try:
        idx = int(ans) - 1 if ans else default_ref - 1
        if not (0 <= idx < len(refs)):
            print("  error: invalid choice.")
            return None
        ref = refs[idx]
    except ValueError:
        if ans in refs:
            ref = ans
        else:
            print("  error: invalid choice.")
            return None

    name = input("  New flake host name (e.g. laptop): ").strip()
    if not name:
        print("  error: name is required.")
        return None

    err = validate_new_host(name, ref)
    if err:
        print(err)
        return None

    bootloader, device = _ask_bootloader(dry_run=False)
    _print_boot_plan(name, bootloader, device)
    if not confirm(f"Create host '{name}' and continue bootstrap?", default=False):
        print("  Cancelled.")
        return None

    create_host_files(name, ref, bootloader, device)
    return name


def _finalize_bootstrap(host: str, *, resume: bool = False, force_hw: bool = False) -> bool:
    if not _copy_hardware(host, resume=resume, force_hw=force_hw):
        return False
    if not _link_etc():
        return False
    if not _rebuild(host):
        return False

    store = load_store()
    store["machine"] = host
    store["host"] = host
    store["created"] = datetime.date.today().isoformat()
    save_store(store)
    print(f"  done: machine {host!r} saved in .nixctl-store")

    _flathub()
    return True


def _copy_hardware(host: str, *, resume: bool = False, force_hw: bool = False) -> bool:
    src = "/etc/nixos/hardware-configuration.nix"
    host_dir = os.path.join(HOSTS_DIR, host)
    os.makedirs(host_dir, exist_ok=True)
    dst = os.path.join(host_dir, "hardware-configuration.nix")

    if os.path.isfile(dst) and resume and not force_hw:
        print(f"  — Skipping hardware copy (already exists: {dst})")
        print("    Re-copy with: nixctl bootstrap --resume --force-hardware")
        return True

    if not os.path.isfile(src):
        print(f"  error: {src} not found")
        print("    Run: sudo nixos-generate-config")
        return False

    shutil.copy2(src, dst)
    print(f"  done: {src} -> {dst}")

    import subprocess

    result = subprocess.run(
        ["git", "add", dst],
        capture_output=True, text=True, cwd=NIXOS_DIR,
    )
    if result.returncode == 0:
        print(f"  done: git add hosts/{host}/hardware-configuration.nix")
    else:
        print(f"  warning: git add failed: {result.stderr.strip()}")
        print(
            f"    Run manually: cd ~/nixos && git add "
            f"hosts/{host}/hardware-configuration.nix"
        )

    return True


def _link_etc() -> bool:
    etc = "/etc/nixos"

    if os.path.islink(etc) and os.readlink(etc) == NIXOS_DIR:
        print(f"  -- /etc/nixos already points to {NIXOS_DIR}")
        return True

    if os.path.exists(etc) or os.path.islink(etc):
        if not confirm(f"Replace /etc/nixos with a symlink to {NIXOS_DIR}?", default=True):
            return False

    code, _ = exec_shell(f"sudo rm -rf {etc} && sudo ln -s {NIXOS_DIR} {etc}")
    if code == 0:
        print(f"  done: /etc/nixos -> {NIXOS_DIR}")
        return True
    print("  error: could not create symlink for /etc/nixos")
    return False


def _rebuild(host: str) -> bool:
    target = flake_target(host)
    print(f"  -> nixos-rebuild switch ({target})")
    print("    (first build may take several minutes)")

    code, _ = exec_shell(f"sudo nixos-rebuild switch --flake {target}")
    if code == 0:
        print("  done: system built")
        return True
    print(f"  error: nixos-rebuild failed (exit {code})")
    return False


def _flathub():
    code, _ = exec_shell(
        "flatpak remote-add --if-not-exists flathub "
        "https://flathub.org/repo/flathub.flatpakrepo 2>/dev/null",
        capture=True,
    )
    print("  done: Flathub remote configured" if code == 0 else "  -- Flathub: skipped or failed")
