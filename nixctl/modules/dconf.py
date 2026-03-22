"""
dconf.py — GNOME settings management via dconf

nixctl dconf apply [--select]
nixctl dconf dump
"""

import re
import os
import curses

from .config import NIXOS_DIR, HOME_NIX, DCONF_FILE, exec_shell

HELP = """\
nixctl dconf <command>

  apply            dump dconf + insert all sections into home.nix
  apply --select   same, but with interactive section picker
  dump             only save current settings to dconf-backup.txt
"""

MARKER_BEGIN = "# DCONF_BEGIN"
MARKER_END   = "# DCONF_END"


def run(args: list):
    if not args or args[0] in ("-h", "--help"):
        print(HELP); return

    cmd    = args[0]
    select = "--select" in args

    if cmd == "apply":
        dump()
        apply(select=select)
    elif cmd == "dump":
        dump()
    else:
        print(f"  Unknown command: dconf {cmd}")
        print(HELP)


# ---------------------------------------------------------------------------
# Dump
# ---------------------------------------------------------------------------

def dump(path: str = DCONF_FILE) -> bool:
    code, _ = exec_shell(f"dconf dump / > {path}")
    if code == 0:
        print(f"  done: saved: {path}")
        return True
    print("  error: dconf dump failed")
    return False


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def apply(select: bool = False,
          dconf_path: str = DCONF_FILE,
          home_nix: str = HOME_NIX):
    if not os.path.exists(dconf_path):
        print(f"  error: not found: {dconf_path}"); return
    if not os.path.exists(home_nix):
        print(f"  error: not found: {home_nix}"); return

    sections = parse_dconf(dconf_path)
    print(f"  Sections found: {len(sections)}")

    if select:
        sections = tui_select(sections)
        if not sections:
            print("  Cancelled."); return
        print(f"  Selected: {len(sections)}")

    nix_block = "\n".join(section_to_nix(s) for s in sections)
    inject(nix_block, home_nix)


# ---------------------------------------------------------------------------
# Parsing dconf-backup.txt
# ---------------------------------------------------------------------------

def parse_dconf(path: str) -> list[dict]:
    sections, current = [], None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = re.match(r"^\[(.+)\]$", line)
            if m:
                current = {"path": m.group(1), "keys": []}
                sections.append(current)
            elif line.strip() and current and "=" in line:
                key, _, val = line.partition("=")
                current["keys"].append((key.strip(), val.strip()))
    return sections


# ---------------------------------------------------------------------------
# GVariant → Nix conversion
# ---------------------------------------------------------------------------

def convert_value(raw: str) -> str:
    raw = raw.strip()

    m = re.match(r"^(int64|uint64)\s+(.+)$", raw)
    if m:
        return f"(lib.hm.gvariant.mkInt64 {m.group(2)})"

    m = re.match(r"^uint32\s+(.+)$", raw)
    if m:
        return f"(lib.hm.gvariant.mkUint32 {m.group(1)})"

    if raw in ("@as []", "@av []"):
        return "[]"
    if raw == "true":  return "true"
    if raw == "false": return "false"

    if re.match(r"^-?\d+$", raw):
        n = int(raw)
        if n < -2_147_483_648 or n > 2_147_483_647:
            return f"(lib.hm.gvariant.mkInt64 {raw})"
        return raw

    if re.match(r"^-?\d+\.\d+$", raw):
        return raw

    if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
        return f'"{raw[1:-1].replace(chr(34), chr(92) + chr(34))}"'

    if raw.startswith("(") and raw.endswith(")"):
        return _tuple(raw)

    if raw.startswith("[") and raw.endswith("]"):
        return _array(raw)

    if raw.startswith("<") and raw.endswith(">"):
        return convert_value(raw[1:-1])

    return f'"{raw.replace(chr(34), chr(92) + chr(34))}"'


def _array(raw: str) -> str:
    inner = raw[1:-1].strip()
    if not inner:
        return "[]"
    return "[ " + " ".join(convert_value(e.strip()) for e in _split(inner)) + " ]"


def _tuple(raw: str) -> str:
    parts = [convert_value(e.strip()) for e in _split(raw[1:-1].strip())]
    return "(lib.hm.gvariant.mkTuple [ " + " ".join(parts) + " ])"


def _split(s: str) -> list[str]:
    elements, depth, in_str, buf = [], 0, False, []
    for i, c in enumerate(s):
        if in_str:
            buf.append(c)
            if c == "'" and (i == 0 or s[i-1] != "\\"):
                in_str = False
        elif c == "'":
            in_str = True; buf.append(c)
        elif c in "([<{":
            depth += 1; buf.append(c)
        elif c in ")]>}":
            depth -= 1; buf.append(c)
        elif c == "," and depth == 0:
            elements.append("".join(buf).strip()); buf = []
        else:
            buf.append(c)
    if buf:
        elements.append("".join(buf).strip())
    return [e for e in elements if e]


def section_to_nix(section: dict, indent: str = "    ") -> str:
    lines = [f'{indent}"{section["path"]}" = {{']
    for key, raw in section["keys"]:
        lines.append(f'{indent}  {key} = {convert_value(raw)};')
    lines.append(f'{indent}}};')
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Injection into home.nix
# ---------------------------------------------------------------------------

def inject(nix_block: str, home_nix: str):
    with open(home_nix, encoding="utf-8") as f:
        content = f.read()

    bi = content.find(MARKER_BEGIN)
    ei = content.find(MARKER_END)

    if bi == -1 or ei == -1:
        print(f"  error: markers {MARKER_BEGIN!r} / {MARKER_END!r} not found in {home_nix}")
        print("    Add them inside dconf.settings = { ... } in home.nix")
        return

    line_start  = content.rfind("\n", 0, ei) + 1
    base_indent = content[line_start:ei]
    if base_indent.strip():
        base_indent = "    "

    new_content = (
        content[:bi]
        + MARKER_BEGIN + "\n"
        + nix_block
        + base_indent + MARKER_END
        + content[ei + len(MARKER_END):]
    )

    with open(home_nix + ".bak", "w", encoding="utf-8") as f:
        f.write(content)

    with open(home_nix, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"  done: home.nix updated  (backup: {home_nix}.bak)")


# ---------------------------------------------------------------------------
# TUI section picker
# ---------------------------------------------------------------------------

def tui_select(sections: list[dict]) -> list[dict]:
    selected = [True] * len(sections)
    state    = {"cursor": 0, "offset": 0, "cancelled": False}

    def draw(stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)

        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            vis  = max(1, h - 5)
            cur, off = state["cursor"], state["offset"]

            title = " nixctl dconf — select sections "
            stdscr.addstr(0, max(0, (w - len(title)) // 2), title,
                          curses.color_pair(3) | curses.A_BOLD)
            hints = "[↑↓/jk] navigate  [Space] toggle  [A] all  [N] none  [Enter] apply  [Q] cancel"
            stdscr.addstr(1, 0, hints[:w - 1])
            stdscr.addstr(2, 0, "-" * (w - 1))

            if cur < off: off = cur
            elif cur >= off + vis: off = cur - vis + 1
            state["offset"] = off

            for i in range(vis):
                idx = off + i
                if idx >= len(sections): break
                mark  = "[x]" if selected[idx] else "[ ]"
                nkeys = len(sections[idx]["keys"])
                label = f" {mark} {sections[idx]['path']}  ({nkeys} keys)"
                row   = 3 + i
                if idx == cur:
                    stdscr.addstr(row, 0, label[:w-1].ljust(w-1), curses.color_pair(1))
                else:
                    stdscr.addstr(row, 0, label[:w-1],
                                  curses.color_pair(2) if selected[idx] else 0)

            status = f" Selected: {sum(selected)}/{len(sections)}  PgUp/PgDn to scroll "
            stdscr.addstr(h - 1, 0, status[:w-1], curses.A_REVERSE)
            stdscr.refresh()

            key = stdscr.getch()
            if key in (curses.KEY_UP, ord("k")):    state["cursor"] = max(0, cur-1)
            elif key in (curses.KEY_DOWN, ord("j")): state["cursor"] = min(len(sections)-1, cur+1)
            elif key == curses.KEY_PPAGE: state["cursor"] = max(0, cur-vis)
            elif key == curses.KEY_NPAGE: state["cursor"] = min(len(sections)-1, cur+vis)
            elif key == curses.KEY_HOME:  state["cursor"] = 0
            elif key == curses.KEY_END:   state["cursor"] = len(sections)-1
            elif key == ord(" "):
                selected[cur] = not selected[cur]
                state["cursor"] = min(len(sections)-1, cur+1)
            elif key in (ord("a"), ord("A")):
                for j in range(len(selected)): selected[j] = True
            elif key in (ord("n"), ord("N")):
                for j in range(len(selected)): selected[j] = False
            elif key in (10, 13, curses.KEY_ENTER): return
            elif key in (ord("q"), ord("Q"), 27):
                state["cancelled"] = True; return

    curses.wrapper(draw)
    if state["cancelled"]:
        return []
    return [s for s, sel in zip(sections, selected) if sel]
