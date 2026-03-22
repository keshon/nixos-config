"""
modules/host.py — flake machines and profiles (nixctl host …)
"""

import os
import shutil
import subprocess

from .config import (
    NIXOS_DIR, HOSTS_DIR, FLAKE_NIX, STORE_FILE,
    REFERENCES_DIR, REFERENCE_DEFAULT,
    load_store, save_store, get_store_value, set_store_value,
    confirm, _hosts_from_flake, FLAKE_TMPL,
    parse_flake_host_entry, packages_list_path, get_environment,
)

HELP = """\
nixctl host <command>

  list              list flake configurations (this machine marked with *)
  new  <n> [--from <ref>]   create a new machine entry + hosts/<n>/ (template ref)
  use  <n>   [advanced]     point software profile at another flake name (same hardware)
  remove <n>                remove a flake entry and its hosts/<n>/ tree
  info [<n>]                show flake paths and files for this or another name

Flags:
  --dry-run       new/use: show planned changes only (no files, no flake edits)
  --from <ref>    new: set ref in flake (references/<ref>/home.nix must exist)
"""



def _parse_flags(rest: list) -> tuple[list, bool]:
    out, dry = [], False
    for a in rest:
        if a == "--dry-run":
            dry = True
        else:
            out.append(a)
    return out, dry


def _parse_new_host_args(rest: list) -> tuple[list, str]:
    """Parse host name and optional --from <ref>. Returns (positional_args, ref)."""
    out, ref = [], REFERENCE_DEFAULT
    i = 0
    while i < len(rest):
        if rest[i] == "--from" and i + 1 < len(rest):
            ref = rest[i + 1]
            i += 2
        else:
            out.append(rest[i])
            i += 1
    return out, ref


def run(args: list):
    if not args or args[0] in ("-h", "--help"):
        print(HELP); return

    cmd, rest = args[0], args[1:]
    rest, dry_run = _parse_flags(rest)

    if cmd == "list":
        list_hosts()
    elif cmd == "new":
        if not rest:
            print("  error: name required (example: nixctl host new laptop)"); return
        new_args, ref = _parse_new_host_args(rest)
        if not new_args:
            print("  error: name required (example: nixctl host new laptop --from minimal)"); return
        new_host(new_args[0], ref=ref, dry_run=dry_run)
    elif cmd == "use":
        if not rest:
            print("  error: name required (example: nixctl host use laptop)"); return
        use_host(rest[0], dry_run=dry_run)
    elif cmd == "remove":
        if not rest:
            print("  error: name required (example: nixctl host remove laptop)"); return
        remove_host(rest[0])
    elif cmd == "info":
        info_host(rest[0] if rest else None)
    else:
        print(f"  Unknown command: host {cmd}")
        print(HELP)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

def list_hosts():
    hosts = _hosts_from_flake()
    machine = get_store_value("machine") or _detect_machine()
    get_environment()
    env_here, hw_here, ref_here = parse_flake_host_entry(machine)

    if not hosts:
        print("  No flake configurations found (nixosConfigurations).")
        print("  Create one: nixctl host new <name>")
        return

    print()
    print(f"  Flake configurations ({len(hosts)})")
    print()
    print("  This machine")
    print(f"    flake name (rebuild #…):  {machine}")
    print(f"    software profile:         {env_here}   (under hosts/{env_here}/)")
    print(f"    hardware:                 {hw_here}   (under hosts/{hw_here}/)")
    if ref_here != REFERENCE_DEFAULT:
        print(f"    reference template:       {ref_here}")
    print()
    print(f"    {'FLAKE':<14} {'PROFILE':<12} {'HARDWARE':<12} {'REF':<10} {'HW-CONF'}")
    print("  " + "-" * 64)
    for h in sorted(hosts):
        env_h, hw_h, ref = parse_flake_host_entry(h)
        hw_ok = os.path.isfile(
            os.path.join(HOSTS_DIR, hw_h, "hardware-configuration.nix")
        )
        ref_s = ref if ref != REFERENCE_DEFAULT else "default"
        star = "*" if h == machine else " "
        conf = "yes" if hw_ok else "no"
        print(
            f"  {star} {h:<12} {env_h:<12} {hw_h:<12} {ref_s:<10} {conf}"
        )
    print()
    print("  * = this machine. PROFILE = software (packages, host.nix). HARDWARE = disks / boot.")
    print("  HW-CONF = hardware-configuration.nix exists under hosts/<HARDWARE>/.")


# ---------------------------------------------------------------------------
# new
# ---------------------------------------------------------------------------

def validate_new_host(name: str, ref: str | None = None) -> str | None:
    """Return an error message if the host cannot be created, else None."""
    if ref is None:
        ref = REFERENCE_DEFAULT
    if not name.replace("-", "").replace("_", "").isalnum():
        return f"  error: invalid name {name!r} (use letters, digits, - and _ only)"

    ref_path = os.path.join(REFERENCES_DIR, ref, "home.nix")
    if not os.path.isfile(ref_path):
        return (
            f"  error: reference {ref!r} not found: {ref_path}\n"
            f"  See: nixctl reference list"
        )

    host_dir = os.path.join(HOSTS_DIR, name)
    if os.path.isdir(host_dir):
        return (
            f"  error: {name!r} already exists: {host_dir}\n"
            f"  Use bootstrap with an existing name, or pick another name."
        )

    hosts = _hosts_from_flake()
    if hosts and name in hosts:
        return (
            f"  error: {name!r} is already in flake.nix\n"
            f"  Use bootstrap with an existing entry, or pick another name."
        )
    return None


def create_host_files(name: str, ref: str, bootloader: str, device: str) -> bool:
    """Create hosts/<name>/, update flake.nix, git add. Caller must validate first."""
    host_dir = os.path.join(HOSTS_DIR, name)
    os.makedirs(host_dir, exist_ok=True)
    _write_host_nix(name, host_dir, bootloader, device)
    _write_packages_nix(name, host_dir)
    print(f"  done: created hosts/{name}/")

    ok = _update_flake_add(name, ref=ref)
    if ok:
        print("  done: flake.nix updated")
    else:
        print("  warning: flake.nix not updated; add the host to flake.nix manually")

    _git_add(host_dir)
    _git_add(FLAKE_NIX)
    return ok


def new_host(name: str, ref: str | None = None, dry_run: bool = False):
    if ref is None:
        ref = REFERENCE_DEFAULT

    err = validate_new_host(name, ref)
    if err:
        print(err)
        return

    bootloader, device = _ask_bootloader(dry_run=dry_run)
    _print_boot_plan(name, bootloader, device)
    if dry_run:
        dr = "UEFI" if _firmware_is_uefi() else "BIOS + GRUB on /dev/sda"
        print(f"  (dry-run defaults: {dr} — run without --dry-run to choose)")
        print()
        print("  [dry-run] No files written. Run without --dry-run to create the host.")
        return

    if not confirm(f"Create host '{name}' with this boot configuration?", default=False):
        print("  Cancelled.")
        return

    create_host_files(name, ref, bootloader, device)

    print()
    print(f"  Next steps for '{name}':")
    print(f"    1. Review hosts/{name}/host.nix (hostname) and hosts/{name}/boot.nix (bootloader)")
    print(f"    2. Reference profile in flake: ref = \"{ref}\" (references/{ref}/home.nix)")
    print(f"    3. Add hardware-configuration.nix from nixos-generate-config when on real hardware")
    print(f"       (or use nixctl bootstrap on a new machine)")


# ---------------------------------------------------------------------------
# use
# ---------------------------------------------------------------------------

def use_host(name: str, dry_run: bool = False):
    hosts   = _hosts_from_flake()
    machine = get_store_value("machine") or _detect_machine()
    env_now, _, _ = parse_flake_host_entry(machine)

    if hosts and name not in hosts:
        print(f"  error: no flake entry {name!r}")
        print(f"  Available: {', '.join(hosts)}")
        return

    if name == env_now:
        print(f"  Already using software profile {name!r} (see flake for this machine).")
        return

    prev = env_now
    print(f"  Switching software profile: {prev} -> {name}")

    # Предупреждение если переключаемся на чужое окружение
    if name != machine:
        print()
        print("  warning: you are borrowing another flake entry's software profile.")
        print(f"  warning: hardware (disks, boot) stays on this machine: {machine!r}")
        print(f"  warning: rebuild would use packages from profile {name!r} and hardware from {machine!r}.")
        print(f"  Boot loader: hosts/{machine}/boot.nix (this machine), not hosts/{name}/boot.nix")
        _warn_env_boot_mismatch(machine, name)
        print()
        print("  Safe uses:")
        print("    - inspect or edit another profile's packages (nixctl pkg list)")
        print("    - compare user-packages.nix between machines")
        print()
        print("  warning: do not run nixctl sys rebuild / nixr unless you intend to apply this mix.")
        print()
        if dry_run:
            print("  [dry-run] Would ask confirmation, then update flake + .nixctl-store.")
            print("  [dry-run] Run without --dry-run to apply.")
            return
        if not confirm(f"Switch environment to '{name}'?", default=False):
            print("  Cancelled."); return
    elif dry_run:
        print()
        print(f"  [dry-run] Would set active env to '{name}' (same machine, env == hw).")
        print("  [dry-run] Run without --dry-run to apply.")
        return

    # Обновляем flake.nix: hw = machine, env = name
    if _update_flake_env(machine=machine, env=name):
        print(f"  done: flake.nix updated (hardware={machine}, profile={name})")
    else:
        print("  warning: flake.nix could not be updated")

    set_store_value("host", name)
    print(f"  done: software profile for this machine is now {name!r}")

    if name != machine:
        print()
        print(f"  To point back at the default tree for this machine: nixctl host use {machine}")

    print()
    print("  Profile change applies after a rebuild.")
    from .config import confirm as _confirm
    if _confirm("Rebuild now? (nixctl sys rebuild)", default=True):
        from .sys import rebuild
        rebuild()
    else:
        print("  Run when ready: nixctl sys rebuild  (or your nixr alias)")


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------

def remove_host(name: str):
    machine = get_store_value("machine") or _detect_machine()
    active_env, _, _ = parse_flake_host_entry(machine)

    if name == machine:
        print(f"  error: cannot remove this machine's flake entry ({name!r})")
        return

    host_dir = os.path.join(HOSTS_DIR, name)
    if not os.path.isdir(host_dir):
        print(f"  error: directory not found: {host_dir}")
        return

    print(f"  Remove flake entry {name!r}:")
    print(f"    directory: {host_dir}")
    print("    flake.nix: entry will be removed")

    if not confirm(f"Remove {name!r}? This cannot be undone.", default=False):
        print("  Cancelled."); return

    # Если удаляем active environment — возвращаемся на своё
    if active_env == name:
        set_store_value("host", machine)
        _update_flake_env(machine=machine, env=machine)
        print(f"  -> Software profile reset to {machine!r} (matches this machine name).")

    # Удаляем папку
    shutil.rmtree(host_dir)
    print(f"  done: removed {host_dir}")

    if _update_flake_remove(name):
        print("  done: flake.nix updated")

    _git_add(FLAKE_NIX)
    print(f"  done: removed flake entry {name!r}")


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------

def info_host(name: str | None = None):
    machine = get_store_value("machine") or _detect_machine()
    target = name or machine

    env_p, hw_p, ref_p = parse_flake_host_entry(target)
    hw_dir = os.path.join(HOSTS_DIR, hw_p)
    env_dir = os.path.join(HOSTS_DIR, env_p)

    print(f"  Flake name (nixosConfigurations): {target}")
    print(f"  profile (software): {env_p}   -> {env_dir}/")
    print(f"  hardware (disks, boot): {hw_p}   -> {hw_dir}/")
    print(f"  reference: {ref_p}")

    print("  Files (hardware / boot):")
    for f in ("hardware-configuration.nix", "boot.nix"):
        path = os.path.join(hw_dir, f)
        mark = "yes" if os.path.isfile(path) else "no"
        print(f"    [{mark}] {f}")

    print("  Files (profile / packages):")
    for f in ("host.nix", "packages.nix", "user-packages.nix"):
        path = os.path.join(env_dir, f)
        mark = "yes" if os.path.isfile(path) else "no"
        print(f"    [{mark}] {f}")

    from .pkg import _read_packages
    pkg_file = packages_list_path(env_p)
    pkgs = _read_packages(pkg_file)
    if pkgs:
        print(f"  Packages ({len(pkgs)}): {', '.join(pkgs[:8])}" +
              (f" ... +{len(pkgs)-8}" if len(pkgs) > 8 else ""))

    store = load_store()
    print(f"  .nixctl-store: machine={store.get('machine','?')}, "
          f"host={store.get('host','?')} (mirrors flake env for this machine), "
          f"created={store.get('created','?')}")


# ---------------------------------------------------------------------------
# Работа с flake.nix через шаблон
# ---------------------------------------------------------------------------

def _render_flake(hosts_config: dict[str, dict], tmpl_path: str | None = None) -> str:
    """
    Читает flake.tmpl.nix и заменяет __HOSTS__ на список хостов.

    hosts_config = {
      "desktop": {"env": "desktop", "hw": "desktop", "ref": "minimal"},
      "laptop":  {"env": "laptop",  "hw": "laptop",  "ref": "minimal"},
    }
    """
    import modules.config as _cfg
    tmpl_path = tmpl_path or _cfg.FLAKE_TMPL
    if not os.path.isfile(tmpl_path):
        raise FileNotFoundError(f"Template not found: {tmpl_path}")

    with open(tmpl_path, encoding="utf-8") as f:
        tmpl = f.read()

    lines = []
    for host, cfg in sorted(hosts_config.items()):
        env = cfg["env"]
        hw  = cfg["hw"]
        ref = cfg.get("ref", REFERENCE_DEFAULT)
        if env == hw and ref == REFERENCE_DEFAULT:
            # Обычный случай — короткая запись (ref по умолчанию в mkHost)
            lines.append(f'      {host} = mkHost {{ env = "{env}"; hw = "{hw}"; }};')
        elif env == hw:
            lines.append(
                f'      {host} = mkHost {{ env = "{env}"; hw = "{hw}"; ref = "{ref}"; }};'
            )
        else:
            # Нестандартное окружение — с комментарием
            if ref == REFERENCE_DEFAULT:
                lines.append(
                    f'      {host} = mkHost {{ env = "{env}"; hw = "{hw}"; }};'
                    f'  # profile {env} + hardware {hw}'
                )
            else:
                lines.append(
                    f'      {host} = mkHost {{ env = "{env}"; hw = "{hw}"; ref = "{ref}"; }};'
                    f'  # profile {env} + hardware {hw}'
                )

    hosts_block = "\n".join(lines)
    return tmpl.replace("__HOSTS__", hosts_block)


def _current_hosts_config() -> dict[str, dict]:
    """Читает текущие хосты из flake.nix (через nix eval или парсинг)."""
    # Пробуем через nix eval
    hosts = _hosts_from_flake()
    if not hosts:
        # Fallback: читаем папки из hosts/
        if os.path.isdir(HOSTS_DIR):
            hosts = [d for d in os.listdir(HOSTS_DIR)
                     if os.path.isdir(os.path.join(HOSTS_DIR, d))]
        else:
            hosts = []

    # Определяем текущий env/hw/ref для каждого хоста из flake.nix
    config = {}
    for h in hosts:
        env, hw, ref = parse_flake_host_entry(h)
        config[h] = {"env": env or h, "hw": hw or h, "ref": ref}
    return config


def _parse_host_flake(host: str) -> tuple[str | None, str | None, str]:
    """Backward-compatible wrapper; see parse_flake_host_entry in config."""
    e, h, r = parse_flake_host_entry(host)
    return e, h, r


def _update_flake_add(new_host: str, ref: str | None = None) -> bool:
    """Добавляет новый хост в flake.nix."""
    if ref is None:
        ref = REFERENCE_DEFAULT
    config = _current_hosts_config()
    config[new_host] = {"env": new_host, "hw": new_host, "ref": ref}
    return _write_flake(config)


def _update_flake_remove(host: str) -> bool:
    """Удаляет хост из flake.nix."""
    config = _current_hosts_config()
    config.pop(host, None)
    return _write_flake(config)


def _update_flake_env(machine: str, env: str) -> bool:
    """Обновляет env для машины machine в flake.nix.

    hw всегда = machine (железо текущей машины, никогда не меняется).
    env = выбранное окружение.
    """
    config = _current_hosts_config()

    # Убеждаемся что все существующие хосты имеют правильный hw
    # (защита от случая когда старый flake.nix был без env/hw)
    for h in list(config.keys()):
        if config[h].get("hw") != h:
            # hw должен совпадать с именем хоста — исправляем
            config[h]["hw"] = h
        config[h].setdefault("ref", REFERENCE_DEFAULT)

    # Обновляем env для текущей машины (ref сохраняем)
    if machine not in config:
        config[machine] = {"env": env, "hw": machine, "ref": REFERENCE_DEFAULT}
    else:
        config[machine]["env"] = env
        config[machine]["hw"]  = machine  # ВСЕГДА железо текущей машины
        config[machine].setdefault("ref", REFERENCE_DEFAULT)

    return _write_flake(config)


def _write_flake(config: dict[str, dict]) -> bool:
    """Рендерит шаблон и записывает flake.nix."""
    try:
        content = _render_flake(config)
        # Бэкап
        if os.path.isfile(FLAKE_NIX):
            shutil.copy2(FLAKE_NIX, FLAKE_NIX + ".bak")
        with open(FLAKE_NIX, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"  error: could not write flake.nix: {e}")
        return False


# ---------------------------------------------------------------------------
# Вспомогательное
# ---------------------------------------------------------------------------

def _detect_machine() -> str:
    """Определяет имя машины из hostname."""
    import platform
    node = platform.node().lower().split(".")[0]
    return node.removeprefix("nixos-")


def _print_boot_plan(name: str, bootloader: str, device: str):
    print(f"  Planned boot settings for hosts/{name}/boot.nix:")
    if bootloader == "uefi":
        print("    • systemd-boot + EFI variables")
    else:
        print(f"    • GRUB on BIOS, device {device}")


def _warn_env_boot_mismatch(machine: str, env: str):
    """Warn when the target env's host.nix still defines boot (legacy; risky when env ≠ hw).

    Boot loader for the running system always comes from hosts/<hw>/boot.nix; host.nix
    from the selected env should not set boot.*.
    """
    host_nix = os.path.join(HOSTS_DIR, env, "host.nix")
    if not os.path.isfile(host_nix):
        return
    try:
        with open(host_nix, encoding="utf-8") as f:
            txt = f.read()
        if "boot.loader" in txt or "boot.initrd" in txt:
            print()
            print(f"  warning: hosts/{env}/host.nix still contains boot.*")
            print("     That file is merged when profile != hardware and can conflict with")
            print(f"     hosts/{machine}/boot.nix. Remove boot.* from host.nix (use boot.nix for the loader).")
    except Exception:
        pass


def _firmware_is_uefi() -> bool:
    """True if the running system firmware exposes an EFI runtime (typical on laptops)."""
    return os.path.isdir("/sys/firmware/efi")


def _ask_bootloader(dry_run: bool = False) -> tuple[str, str]:
    """Ask bootloader type and (for BIOS) disk device.
    Returns ('bios', '/dev/sda') or ('uefi', '').
    """
    uefi = _firmware_is_uefi()
    if dry_run:
        return ("uefi", "") if uefi else ("bios", "/dev/sda")

    print()
    if uefi:
        print("  Firmware reports UEFI (/sys/firmware/efi). systemd-boot is recommended.")
        print("  Only choose BIOS + GRUB if you know this machine boots in legacy mode.")
    else:
        print("  No EFI sysfs tree: treating as legacy BIOS / VM without UEFI.")
    print()
    print("  Bootloader type:")
    print("    [1] Legacy BIOS + GRUB  (VMs, older hardware)")
    print("    [2] UEFI + systemd-boot (typical for current laptops)")
    default_choice = "2" if uefi else "1"
    ans = input(f"  Choice [{default_choice}]: ").strip()
    if not ans:
        ans = default_choice

    if ans == "2":
        return "uefi", ""

    if uefi:
        print()
        print("  warning: BIOS + GRUB on a system that exposes UEFI may not boot.")
        print("  Fix later: edit hosts/<hw>/boot.nix or run scripts/set-boot-uefi.sh from the repo.")

    # BIOS: ask for disk device
    # Try to detect available disks
    import subprocess
    try:
        result = subprocess.run(
            ["lsblk", "-dno", "NAME,SIZE,TYPE"],
            capture_output=True, text=True
        )
        disks = [
            line.split() for line in result.stdout.splitlines()
            if "disk" in line
        ]
        if disks:
            print()
            print("  Available disks:")
            for d in disks:
                name = d[0]
                size = d[1] if len(d) > 1 else "?"
                print(f"    /dev/{name}  ({size})")
    except Exception:
        pass

    device = input("  System disk [/dev/sda]: ").strip()
    if not device:
        device = "/dev/sda"
    if not device.startswith("/dev/"):
        device = f"/dev/{device}"

    return "bios", device


def _write_host_nix(name: str, host_dir: str,
                    bootloader: str = "bios", device: str = "/dev/sda"):
    """Generate host.nix (hostname) and boot.nix (bootloader for this machine's hw)."""
    host_path = os.path.join(host_dir, "host.nix")
    boot_path = os.path.join(host_dir, "boot.nix")

    if bootloader == "uefi":
        boot_block = (
            "  # UEFI bootloader\n"
            "  boot.loader.systemd-boot.enable      = true;\n"
            "  boot.loader.efi.canTouchEfiVariables = true;\n"
        )
    else:
        boot_block = (
            "  # Legacy BIOS + GRUB\n"
            "  boot.loader.grub.enable      = true;\n"
            "  boot.loader.grub.useOSProber = true;\n"
            f"  boot.loader.grub.device      = \"{device}\";\n"
        )

    with open(boot_path, "w", encoding="utf-8") as f:
        f.write(
            f"# hosts/{name}/boot.nix — bootloader (imported from hardware profile only)\n"
            f"{{ ... }}:\n\n{{\n"
            f"{boot_block}"
            f"}}\n"
        )

    with open(host_path, "w", encoding="utf-8") as f:
        f.write(
            f"# hosts/{name}/host.nix\n"
            f"# Machine-specific settings for '{name}' (hostname; bootloader is boot.nix)\n"
            f"{{ ... }}:\n\n{{\n"
            f"  networking.hostName = \"nixos-{name}\";\n"
            f"}}\n"
        )


def _write_packages_nix(name: str, host_dir: str):
    """packages.nix pulls nixctl from flake.nix; user list lives in user-packages.nix."""
    up = os.path.join(host_dir, "user-packages.nix")
    with open(up, "w", encoding="utf-8") as f:
        f.write(
            f"# hosts/{name}/user-packages.nix — nixctl pkg add/remove edits this file\n"
            f"# Close the list with `]` only (no semicolon after `]`).\n"
            f"{{ pkgs, ... }}:\n"
            f"with pkgs; [\n"
            f"]\n"
        )
    path = os.path.join(host_dir, "packages.nix")
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            f"# hosts/{name}/packages.nix — nixctl from flake.nix; list in user-packages.nix\n"
            f"{{ pkgs, nixctl, ... }}:\n"
            f"let\n"
            f"  userPkgs = import ./user-packages.nix {{ inherit pkgs; }};\n"
            f"in\n"
            f"{{\n"
            f"  home.packages = with pkgs; [\n"
            f"    nixctl\n"
            f"  ] ++ userPkgs;\n"
            f"}}\n"
        )


def _git_add(path: str):
    """git add для пути (не падает если git недоступен)."""
    try:
        subprocess.run(
            ["git", "add", path],
            capture_output=True, cwd=NIXOS_DIR
        )
    except Exception:
        pass
