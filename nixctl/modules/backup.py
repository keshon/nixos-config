"""
modules/backup.py — ротационные бэкапы конфигов

nixctl backup save
nixctl backup list
nixctl backup restore [n]
"""

import os
import shutil
from datetime import datetime

from .config import NIXOS_DIR, BACKUP_DIR, BACKUP_KEEP, confirm

HELP = """\
nixctl backup <команда>

  save          создать снимок всех конфигов
  list          показать список снимков
  restore [n]   восстановить снимок (по умолчанию последний)
"""

BACKUP_FILES = [
    "home.nix", "configuration.nix", "flake.nix",
    "flake.lock", "dconf-backup.txt",
]
BACKUP_DIRS = ["modules", "hosts", "ui"]


def run(args: list):
    if not args or args[0] in ("-h", "--help"):
        print(HELP); return

    cmd, rest = args[0], args[1:]

    if cmd == "save":
        save()
    elif cmd == "list":
        _print_list()
    elif cmd == "restore":
        lst = list_backups()
        if not lst:
            print("  No snapshots."); return
        n = 0
        if rest:
            try:
                n = int(rest[0]) - 1
            except ValueError:
                print("  Provide a number: nixctl backup restore 2"); return
        n = max(0, min(n, len(lst) - 1))
        restore(lst[n])
    else:
        print(f"  Unknown command: backup {cmd}")
        print(HELP)


def save() -> str | None:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest = os.path.join(BACKUP_DIR, stamp)
    os.makedirs(dest, exist_ok=True)

    count = 0
    for fname in BACKUP_FILES:
        src = os.path.join(NIXOS_DIR, fname)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(dest, fname))
            count += 1

    for dname in BACKUP_DIRS:
        src = os.path.join(NIXOS_DIR, dname)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dest, dname), dirs_exist_ok=True)
            count += 1

    print(f"  ✓ Снимок создан: backups/{stamp}  ({count} items)")
    _rotate()
    return dest


def list_backups() -> list[str]:
    if not os.path.isdir(BACKUP_DIR):
        return []
    return sorted(
        [d for d in os.listdir(BACKUP_DIR)
         if os.path.isdir(os.path.join(BACKUP_DIR, d))],
        reverse=True
    )


def restore(name: str) -> bool:
    src = os.path.join(BACKUP_DIR, name)
    if not os.path.isdir(src):
        print(f"  ✗ Снимок not found: {name}"); return False

    if not confirm(f"Restore from '{name}'? Текущее состояние будет сохранено.", default=False):
        print("  Cancelled."); return False

    # Сначала сохраняем текущее
    print("  → Saving current state...")
    save()

    count = 0
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(NIXOS_DIR, item)
        if os.path.isfile(s):
            shutil.copy2(s, d); count += 1
        elif os.path.isdir(s):
            if os.path.exists(d):
                shutil.rmtree(d)
            shutil.copytree(s, d); count += 1

    print(f"  ✓ Restored from '{name}'  ({count} items)")
    print("    Run 'nixctl sys rebuild' to apply")
    return True


def _print_list():
    lst = list_backups()
    if not lst:
        print("  No snapshots found.")
        return
    print(f"  Snapshots ({len(lst)}, newest first):")
    for i, name in enumerate(lst, 1):
        marker = " ← latest" if i == 1 else ""
        print(f"    [{i}] {name}{marker}")


def _rotate():
    lst = list_backups()
    if len(lst) <= BACKUP_KEEP:
        return
    for name in lst[BACKUP_KEEP:]:
        shutil.rmtree(os.path.join(BACKUP_DIR, name))
    print(f"  → Rotation: removed old snapshots: {len(lst) - BACKUP_KEEP}")
