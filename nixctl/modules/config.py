"""
config.py — shared paths, store, host detection, command execution
"""

import os
import re
import sys
import json
import platform
import subprocess

# ---------------------------------------------------------------------------
# Paths — NIXCTL_DIR env var overrides default ~/nixos
# ---------------------------------------------------------------------------
NIXOS_DIR   = os.environ.get("NIXCTL_DIR", os.path.join(os.path.expanduser("~"), "nixos"))
HOME_NIX    = os.path.join(NIXOS_DIR, "home.nix")
CONFIG_NIX  = os.path.join(NIXOS_DIR, "configuration.nix")
FLAKE_NIX   = os.path.join(NIXOS_DIR, "flake.nix")
FLAKE_TMPL  = os.path.join(NIXOS_DIR, "flake.tmpl.nix")
DCONF_FILE  = os.path.join(NIXOS_DIR, "dconf-backup.txt")
BACKUP_DIR  = os.path.join(NIXOS_DIR, "backups")
HOSTS_DIR   = os.path.join(NIXOS_DIR, "hosts")
REFERENCES_DIR = os.path.join(NIXOS_DIR, "references")
REFERENCE_DEFAULT = "minimal"  # must match references/<name>/ and mkHost default in flake.tmpl.nix
STORE_FILE  = os.path.join(NIXOS_DIR, ".nixctl-store")
BACKUP_KEEP = 10

# ---------------------------------------------------------------------------
# .nixctl-store — local JSON state (gitignored)
# Keys:
#   machine  — hardware identity of this machine, set at bootstrap, never changes
#   host     — legacy mirror of flake env for this machine; synced from flake (authoritative)
#   created  — ISO date of bootstrap
#
# Reference vs machine (mental model):
#   Machine (flake nixosConfigurations.<name>) — concrete PC: hw (disk UUIDs,
#   boot.nix), hostname in host.nix, package overrides. Each entry has env/hw/ref.
#   Reference (references/<ref>/home.nix) — shared "direction" defaults layered
#   between ./home.nix and hosts/<env>/packages.nix; ref is passed as specialArgs
#   and home-manager.extraSpecialArgs. Canonical ref per host lives in flake.nix;
#   optional key "ref" here may mirror it for tooling (not required for builds).
# ---------------------------------------------------------------------------

def load_store() -> dict:
    try:
        with open(STORE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_store(data: dict):
    try:
        with open(STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  error: could not write store: {e}")


def get_store_value(key: str, default=None):
    return load_store().get(key, default)


def set_store_value(key: str, value):
    data = load_store()
    data[key] = value
    save_store(data)


# ---------------------------------------------------------------------------
# Host detection — machine (flake #name) vs environment (hosts/<env>/ packages)
# ---------------------------------------------------------------------------

def parse_flake_host_entry(name: str) -> tuple[str, str, str]:
    """Parse flake.nix for `name = mkHost { ... }`; return (env, hw, ref).

    If the block is missing or unparsable, returns (name, name, REFERENCE_DEFAULT).
    """
    if not os.path.isfile(FLAKE_NIX):
        return name, name, REFERENCE_DEFAULT
    try:
        with open(FLAKE_NIX, encoding="utf-8") as f:
            content = f.read()
        pattern = rf'{re.escape(name)}\s*=\s*mkHost\s*\{{([^}}]*)\}}'
        m = re.search(pattern, content)
        if m:
            inner = m.group(1)
            env_m = re.search(r'env\s*=\s*"([^"]+)"', inner)
            hw_m = re.search(r'hw\s*=\s*"([^"]+)"', inner)
            ref_m = re.search(r'ref\s*=\s*"([^"]+)"', inner)
            env = env_m.group(1) if env_m else name
            hw = hw_m.group(1) if hw_m else name
            ref = ref_m.group(1) if ref_m else REFERENCE_DEFAULT
            return env, hw, ref
    except Exception:
        pass
    return name, name, REFERENCE_DEFAULT


def get_environment() -> str:
    """Package/profile directory name under hosts/<env>/ for this machine's flake entry."""
    m = get_machine()
    env, _hw, _ref = parse_flake_host_entry(m)
    if get_store_value("host") != env:
        set_store_value("host", env)
    return env


def get_host() -> str:
    """Active environment name (same as get_environment(); kept for callers)."""
    return get_environment()


def get_machine() -> str:
    """Returns the hardware identity of this machine (never changes after bootstrap)."""
    return get_store_value("machine") or _hostname_guess()


def packages_nix(host: str | None = None) -> str:
    """Path to packages.nix for the given (or active) host."""
    return os.path.join(HOSTS_DIR, host or get_host(), "packages.nix")


def user_packages_nix(host: str | None = None) -> str:
    """Path to user-packages.nix (editable list) for the given (or active) host."""
    return os.path.join(HOSTS_DIR, host or get_host(), "user-packages.nix")


def packages_list_path(host: str | None = None) -> str:
    """File nixctl pkg edits: user-packages.nix when present, else legacy packages.nix."""
    h = host if host is not None else get_host()
    u = os.path.join(HOSTS_DIR, h, "user-packages.nix")
    if os.path.isfile(u):
        return u
    return packages_nix(h)


def flake_target(host: str | None = None) -> str:
    """
    Returns the nixos-rebuild flake target.
    Always uses the machine (hw), not the active env.
    """
    if host:
        return f"{NIXOS_DIR}#{host}"
    return f"{NIXOS_DIR}#{get_machine()}"


def _hosts_from_flake() -> list[str]:
    """Reads host names from flake.nixosConfigurations via nix eval."""
    try:
        result = subprocess.run(
            ["nix", "eval", ".#nixosConfigurations",
             "--apply", "builtins.attrNames", "--json"],
            capture_output=True, text=True, cwd=NIXOS_DIR, timeout=15
        )
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
    except Exception:
        pass
    # Fallback: read hosts/ directory
    if os.path.isdir(HOSTS_DIR):
        return [d for d in os.listdir(HOSTS_DIR)
                if os.path.isdir(os.path.join(HOSTS_DIR, d))]
    return []


def _hostname_guess() -> str:
    node = platform.node().lower().split(".")[0]
    for prefix in ("nixos-",):
        if node.startswith(prefix):
            return node[len(prefix):]
    return node


# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------

def exec_cmd(cmd: list[str], sudo: bool = False) -> int:
    """Run a command in the current terminal. Returns exit code."""
    if sudo:
        cmd = ["sudo"] + cmd
    return subprocess.run(cmd).returncode


def exec_shell(cmd: str, capture: bool = False) -> tuple[int, str]:
    """Run a shell command. Returns (exit_code, output)."""
    result = subprocess.run(
        cmd, shell=True,
        capture_output=capture, text=True
    )
    return result.returncode, (result.stdout + result.stderr) if capture else ""


def confirm(question: str, default: bool = False) -> bool:
    """Interactive yes/no prompt."""
    hint = "[Y/n]" if default else "[y/N]"
    ans = input(f"  {question} {hint}: ").strip().lower()
    if not ans:
        return default
    return ans in ("y", "yes")
