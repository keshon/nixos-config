"""
modules/pkg.py — package management via hosts/<host>/packages.nix

nixctl pkg search [query]   — interactive search with live filtering
nixctl pkg add    <n>
nixctl pkg remove <n>
nixctl pkg list
"""

import sys
import re
import os
import json
import subprocess
import time

import shutil
from .config import (
    HOME_NIX, NIXOS_DIR, HOSTS_DIR,
    exec_cmd, exec_shell, confirm,
    get_host, packages_nix, packages_list_path,
    _hosts_from_flake,
)

HELP = """\
nixctl pkg <command>

  search [query]    interactive search with live filtering
                    query is optional — type it in the TUI
                    ranking: exact name > name prefix > name word match >
                             name substring > description (word then substring)
  add    <n>   add package directly (without search)
  remove <n>   remove package
  list               list installed packages

Edits hosts/<host>/user-packages.nix when that file exists; otherwise legacy packages.nix.
"""

# Package index cache
_INDEX_CACHE = os.path.join(NIXOS_DIR, ".nixctl-pkg-index.json")
_INDEX_MAX_AGE = 24 * 3600  # refresh once per day

_SKIP = {
    "home", "packages", "with", "pkgs", "let", "in", "rec",
    "writeShellScriptBin", "python3", "withPackages", "ps",
    "textual", "exec", "bin", "lib", "hm", "gvariant",
    "true", "false", "null", "if", "then", "else",
    "mkDerivation", "fetchFromGitHub", "stdenv",
}


def run(args: list):
    if not args or args[0] in ("-h", "--help"):
        print(HELP); return

    cmd, rest = args[0], args[1:]

    if cmd == "search":
        initial_query = rest[0] if rest else ""
        fresh = "--fresh" in rest
        search(initial_query, fresh=fresh)
    elif cmd == "add":
        if not rest:
            print("  Provide a name: nixctl pkg add vlc"); return
        add(rest[0])
    elif cmd == "remove":
        if not rest:
            print("  Provide a name: nixctl pkg remove vlc"); return
        remove(rest[0])
    elif cmd == "list":
        list_pkgs()
    else:
        print(f"  Unknown command: pkg {cmd}")
        print(HELP)


# ---------------------------------------------------------------------------
# Search — interactive TUI with live filtering
# ---------------------------------------------------------------------------

def search(initial_query: str = "", fresh: bool = False):
    """
    Loads package index (from cache or network), then opens an
    interactive TUI where you can type a query and see results instantly.
    """
    if not sys.stdout.isatty():
        # Fallback for non-tty
        results = _load_or_fetch(fresh, progress=True)
        if initial_query:
            results = _filter(results, initial_query)
        chosen = _pick_plain(results[:200])
        if chosen:
            _install_chosen(chosen)
        return

    # Show progress while index loads
    index = _load_or_fetch(fresh, progress=True)
    if not index:
        print("  ✗ Failed to load package index")
        return

    chosen = _search_tui(index, initial_query)
    if not chosen:
        return

    print(f"\n  Selected ({len(chosen)}):")
    for name, desc in chosen:
        print(f"    • {name}  —  {desc[:60]}")

    target_file, _ = _ask_install_target()
    if target_file is None:
        print("  Cancelled."); return

    _insert_chosen_packages(chosen, target_file)
    print(f"  ✓ Added to: {target_file}")
    _maybe_rebuild()


def _search_tui(index: list[tuple[str, str]], initial_query: str = "") -> list[tuple[str, str]]:
    """
    Interactive TUI: input line at top, results list below.
    Filtering happens instantly as you type.
    """
    import curses

    # (name, desc) — unique per row; multiple nixpkgs attrs can share the same name
    selected_items: set[tuple[str, str]] = set()
    state = {
        "query":     list(initial_query),
        "cursor":    0,
        "offset":    0,
        "cancelled": False,
        "results":   _filter(index, initial_query),
    }

    def draw(stdscr):
        curses.curs_set(1)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)   # highlight
        curses.init_pair(2, curses.COLOR_GREEN,  -1)                  # selected
        curses.init_pair(3, curses.COLOR_YELLOW, -1)                  # header
        curses.init_pair(4, curses.COLOR_CYAN,   -1)                  # input line

        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            vis = max(1, h - 6)
            cur = state["cursor"]
            off = state["offset"]
            results = state["results"]
            query_str = "".join(state["query"])

            # Row 0: title
            title = f" nixctl pkg search  [{len(index)} packages in index] "
            stdscr.addstr(0, 0, title[:w-1], curses.color_pair(3) | curses.A_BOLD)

            # Row 1: input field
            prompt = "  Search: "
            stdscr.addstr(1, 0, prompt, curses.color_pair(4))
            qshow = query_str[-(w - len(prompt) - 2):]  # scroll if long
            stdscr.addstr(1, len(prompt), qshow)

            # Row 2: hints
            hints = "[↑↓/PgUp/PgDn] navigate  [Tab] select  [Enter] install  [Esc/Q] cancel"
            stdscr.addstr(2, 0, hints[:w-1], curses.A_DIM)
            stdscr.addstr(3, 0, "─" * (w-1))

            # Scroll
            if cur < off: off = cur
            elif cur >= off + vis: off = cur - vis + 1
            state["offset"] = off

            # Results list
            for i in range(vis):
                idx = off + i
                if idx >= len(results): break
                name, desc = results[idx]
                is_sel = (name, desc) in selected_items
                mark = "[✓]" if is_sel else "[ ]"
                max_desc = max(0, w - 38)
                label = f" {mark} {name:<32} {desc[:max_desc]}"
                row = 4 + i
                if idx == cur:
                    stdscr.addstr(row, 0, label[:w-1].ljust(w-1), curses.color_pair(1))
                else:
                    attr = curses.color_pair(2) if is_sel else 0
                    stdscr.addstr(row, 0, label[:w-1], attr)

            # Status bar
            n_sel = len(selected_items)
            n_res = len(results)
            status = f" Found: {n_res}  |  Selected: {n_sel}  |  Tab to select  Enter to install "
            stdscr.addstr(h-1, 0, status[:w-1], curses.A_REVERSE)

            # Cursor in input field
            cursor_x = min(len(prompt) + len(qshow), w-2)
            stdscr.move(1, cursor_x)
            stdscr.refresh()

            # Key handling
            key = stdscr.getch()

            if key == curses.KEY_UP or key == ord("k") and not state["query"]:
                state["cursor"] = max(0, cur - 1)

            elif key == curses.KEY_DOWN or key == ord("j") and not state["query"]:
                state["cursor"] = min(max(0, len(results)-1), cur + 1)

            elif key == curses.KEY_PPAGE:
                state["cursor"] = max(0, cur - vis)

            elif key == curses.KEY_NPAGE:
                state["cursor"] = min(max(0, len(results)-1), cur + vis)

            elif key == curses.KEY_HOME:
                state["cursor"] = 0

            elif key == curses.KEY_END:
                state["cursor"] = max(0, len(results) - 1)

            elif key == ord("\t"):  # Tab — toggle current row (name+desc is unique)
                if results and cur < len(results):
                    item = results[cur]
                    if item in selected_items:
                        selected_items.discard(item)
                    else:
                        selected_items.add(item)
                    state["cursor"] = min(len(results)-1, cur + 1)

            elif key in (10, 13, curses.KEY_ENTER):  # Enter
                # If nothing selected via Tab — install current row only (one tuple)
                if not selected_items and results and cur < len(results):
                    selected_items.add(results[cur])
                return

            elif key in (27, ):  # Esc
                state["cancelled"] = True; return

            elif key == ord("q") and not state["query"]:
                state["cancelled"] = True; return

            elif key == curses.KEY_BACKSPACE or key == 127:
                if state["query"]:
                    state["query"].pop()
                    state["results"] = _filter(index, "".join(state["query"]))
                    state["cursor"] = 0
                    state["offset"] = 0

            elif 32 <= key <= 126:  # printable characters
                state["query"].append(chr(key))
                state["results"] = _filter(index, "".join(state["query"]))
                state["cursor"] = 0
                state["offset"] = 0

    curses.wrapper(draw)

    if state["cancelled"]:
        return []

    return sorted(selected_items, key=lambda x: (x[0].lower(), x[1]))


def _filter(index: list[tuple[str, str]], query: str) -> list[tuple[str, str]]:
    """Filter and rank matches for the search TUI.

    Ranking (lower rank = earlier in results):
      0 — exact attribute name match (case-insensitive)
      1 — name starts with query
      2 — name contains query at a token boundary (after start or non-alphanumeric)
      3 — name contains query as arbitrary substring
      5 — description: token-boundary match
      6 — description: arbitrary substring

    Up to 500 results are returned.
    """
    if not query:
        return index[:500]
    ranked: list[tuple[int, str, str]] = []
    for name, desc in index:
        rank = _match_rank(name, desc, query)
        if rank is not None:
            ranked.append((rank, name, desc))
    ranked.sort(key=lambda x: (x[0], x[1].lower()))
    return [(n, d) for _, n, d in ranked[:500]]


def _match_rank(name: str, desc: str, query: str) -> int | None:
    """Lower rank = better. None = excluded."""
    ql = query.lower()
    nl = name.lower()
    dl = desc.lower()
    if nl == ql:
        return 0
    if nl.startswith(ql):
        return 1
    if re.search(r"(?:^|[^a-z0-9])" + re.escape(ql), nl):
        return 2
    if ql in nl:
        return 3
    if re.search(r"(?:^|[^a-z0-9])" + re.escape(ql), dl):
        return 5
    if ql in dl:
        return 6
    return None


# ---------------------------------------------------------------------------
# Index loading / cache
# ---------------------------------------------------------------------------

def _load_or_fetch(fresh: bool = False, progress: bool = False) -> list[tuple[str, str]]:
    """
    Load package index.
    Tries local cache .nixctl-pkg-index.json first,
    fetches via nix search if stale or --fresh.
    """
    if not fresh and _cache_fresh():
        if progress:
            count = len(_read_cache())
            print(f"  ✓ Index from cache ({count} packages)")
        return _read_cache()

    if progress:
        print("  → Loading nixpkgs index... (first time ~30s, then cached)")

    index = _fetch_index()
    if index:
        _write_cache(index)
        if progress:
            print(f"  ✓ Index loaded: {len(index)} packages")
    return index


def _cache_fresh() -> bool:
    """Cache exists and is not older than _INDEX_MAX_AGE."""
    if not os.path.isfile(_INDEX_CACHE):
        return False
    age = time.time() - os.path.getmtime(_INDEX_CACHE)
    return age < _INDEX_MAX_AGE


def _read_cache() -> list[tuple[str, str]]:
    try:
        with open(_INDEX_CACHE, encoding="utf-8") as f:
            data = json.load(f)
        return [(item["name"], item.get("desc", "")) for item in data]
    except Exception:
        return []


def _write_cache(index: list[tuple[str, str]]):
    try:
        data = [{"name": n, "desc": d} for n, d in index]
        with open(_INDEX_CACHE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def _fetch_index() -> list[tuple[str, str]]:
    """Fetch full nixpkgs index via nix search."""

    try:
        result = subprocess.run(
            ["nix", "search", "nixpkgs", "", "--json"],
            capture_output=True, text=True, timeout=120, cwd=NIXOS_DIR
        )
        if result.returncode != 0 or not result.stdout.strip():
            return _fetch_index_fallback()
        data = json.loads(result.stdout)
        index = []
        for key, val in data.items():
            name = key.split(".")[-1]
            desc = val.get("description", "")
            index.append((name, desc))
        # Sort by name
        return sorted(index, key=lambda x: x[0])
    except subprocess.TimeoutExpired:
        print("  ⚠ Index fetch timed out, trying fallback...")
        return _fetch_index_fallback()
    except Exception:
        return _fetch_index_fallback()


def _fetch_index_fallback() -> list[tuple[str, str]]:
    """Fallback via nix-env -qaP (faster but fewer descriptions)."""
    try:
        result = subprocess.run(
            ["nix-env", "-qaP"],
            capture_output=True, text=True, timeout=60
        )
        index = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0].replace("nixpkgs.", "")
                index.append((name, ""))
        return sorted(index, key=lambda x: x[0])
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Add / remove
# ---------------------------------------------------------------------------

def add(pkg_name: str) -> bool:
    target_file, scope = _ask_install_target()
    if target_file is None:
        print("  Cancelled."); return False

    existing = _read_packages(target_file)
    if pkg_name in existing:
        print(f"  — '{pkg_name}' already in {os.path.basename(target_file)}")
        return False

    ok = _insert_to_file(pkg_name, target_file)
    if ok:
        print(f"  ✓ Added to: {target_file}")
        _maybe_rebuild()
    return ok


def remove(pkg_name: str) -> bool:
    candidates = _find_package(pkg_name)
    if not candidates:
        print(f"  ✗ '{pkg_name}' not found in any packages.nix or home.nix")
        print("    Check the list: nixctl pkg list"); return False

    if len(candidates) == 1:
        target_file = candidates[0]
    else:
        print(f"  Package found in multiple files:")
        for i, f in enumerate(candidates, 1):
            print(f"    [{i}] {f}")
        ans = input("  Remove from which? [1]: ").strip()
        try:
            target_file = candidates[int(ans) - 1 if ans else 0]
        except (ValueError, IndexError):
            print("  Cancelled."); return False

    if not confirm(f"Remove '{pkg_name}' from {os.path.basename(target_file)}?", default=False):
        print("  Cancelled."); return False

    ok = _remove_from_file(pkg_name, target_file)
    if ok:
        _maybe_rebuild()
    return ok


def list_pkgs():
    host = get_host()
    pkg_file = packages_list_path(host)
    shown_any = False

    if os.path.isfile(pkg_file):
        pkgs = _read_packages(pkg_file)
        if pkgs:
            label = os.path.basename(pkg_file)
            print(f"  [{host}] {label} ({len(pkgs)}):")
            for p in pkgs:
                print(f"    • {p}")
            shown_any = True

    home_pkgs = _read_packages(HOME_NIX)
    if home_pkgs:
        print(f"  [shared] home.nix ({len(home_pkgs)}):")
        for p in home_pkgs:
            print(f"    • {p}")
        shown_any = True

    if not shown_any:
        print(f"  No packages found")
        print(f"  Expected file: {pkg_file}")


# ---------------------------------------------------------------------------
# Install target selection
# ---------------------------------------------------------------------------

def _ask_install_target() -> tuple[str | None, str]:
    hosts = _hosts_from_flake() or [get_host()]
    current = get_host()
    print()
    print("  Where to install?")
    options = []
    pkg_file = packages_list_path(current)
    options.append((f"this machine only ({current})  →  {pkg_file}", pkg_file))
    for h in hosts:
        if h != current:
            f = packages_list_path(h)
            options.append((f"other machine ({h})  →  {f}", f))
    options.append((f"all machines  →  home.nix", HOME_NIX))
    for i, (label, _) in enumerate(options, 1):
        print(f"    [{i}] {label}")
    ans = input(f"  Choice [1]: ").strip()
    try:
        idx = int(ans) - 1 if ans else 0
        if 0 <= idx < len(options):
            return options[idx][1], options[idx][0]
    except ValueError:
        pass
    return None, ""


def _install_chosen(chosen: list[tuple[str, str]]):
    print(f"\n  Selected ({len(chosen)}):")
    for name, desc in chosen:
        print(f"    • {name}  —  {desc[:60]}")
    target_file, _ = _ask_install_target()
    if target_file is None:
        print("  Cancelled."); return
    _insert_chosen_packages(chosen, target_file)
    print(f"  ✓ Added to: {target_file}")
    _maybe_rebuild()


def _pick_plain(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Text fallback for non-tty environments."""
    print()
    for i, (name, desc) in enumerate(items[:50], 1):
        print(f"  {i:3}. {name:<30} {desc[:50]}")
    if len(items) > 50:
        print(f"  ... and {len(items) - 50}")
    ans = input("\n  Numbers separated by space (Enter = cancel): ").strip()
    if not ans: return []
    chosen = []
    for tok in ans.split():
        try:
            idx = int(tok) - 1
            if 0 <= idx < len(items):
                chosen.append(items[idx])
        except ValueError:
            pass
    return chosen


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

def _nix_line_is_comment(stripped: str) -> bool:
    """Whole-line Nix # comment (user-packages.nix style)."""
    return bool(stripped) and stripped.startswith("#")


def _find_with_pkgs_header_line(lines: list[str]) -> int | None:
    """
    Index of the real `with pkgs; [` line — not a # comment (comments may mention
    `with pkgs; [` and would break naive matching).
    """
    for i, line in enumerate(lines):
        stripped = line.strip()
        if _nix_line_is_comment(stripped):
            continue
        if "with pkgs" in line and "[" in line:
            return i
    return None


def _insert_chosen_packages(chosen: list[tuple[str, str]], target_file: str) -> None:
    """
    Insert packages from search/add. Same attribute name can appear on multiple index
    rows — only add each name once. Skip names already in the file.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for name, _desc in sorted(chosen, key=lambda x: (x[0].lower(), x[1])):
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    existing = _read_packages(target_file)
    for name in ordered:
        if name in existing:
            print(f"  — '{name}' already listed, skipping")
            continue
        _insert_to_file(name, target_file)


def _find_with_pkgs_list_insert_line(lines: list[str]) -> int | None:
    """
    Line index to insert a new attribute name: immediately before the `]` that closes
    the first `with pkgs; [` list in the file.
    """
    start = _find_with_pkgs_header_line(lines)
    if start is None:
        return None
    depth = lines[start].count("[") - lines[start].count("]")
    for i in range(start + 1, len(lines)):
        depth += lines[i].count("[") - lines[i].count("]")
        if depth <= 0:
            return i
    return None


def _read_user_packages_nix(path: str) -> list[str]:
    """Parse hosts/<host>/user-packages.nix — only the `with pkgs; [ ... ]` list (close with `]` not `];`)."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []
    in_block = in_shell = False
    skip_expr = depth = 0
    pkgs = []
    for line in lines:
        stripped = line.strip()
        if not in_block:
            if _nix_line_is_comment(stripped):
                continue
            if "with pkgs" in stripped and "[" in stripped:
                in_block = True
                depth = stripped.count("[") - stripped.count("]")
            continue
        depth += stripped.count("[") - stripped.count("]")
        shell_markers = stripped.count("''")
        if shell_markers % 2 == 1:
            in_shell = not in_shell
        if in_shell:
            continue
        if depth <= 0:
            break
        if "writeShellScriptBin" in stripped:
            skip_expr = stripped.count("(") - stripped.count(")")
            continue
        if skip_expr > 0:
            skip_expr += stripped.count("(") - stripped.count(")")
            continue
        if stripped.startswith("(") or "withPackages" in stripped:
            continue
        code = re.sub(r"#.*", "", stripped)
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9._-]*", code):
            if token not in _SKIP and len(token) > 1:
                pkgs.append(token)
    seen, result = set(), []
    for p in pkgs:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


def _read_packages(path: str) -> list[str]:
    if not os.path.isfile(path): return []
    if os.path.basename(path) == "user-packages.nix":
        return _read_user_packages_nix(path)
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []
    in_block = in_shell = False
    skip_expr = depth = 0
    pkgs = []
    for line in lines:
        stripped = line.strip()
        if not in_block:
            if "home.packages" in stripped and "with pkgs" in stripped:
                in_block = True
                depth = stripped.count("[") - stripped.count("]")
            continue
        depth += stripped.count("[") - stripped.count("]")
        if depth <= 0: break
        shell_markers = stripped.count("''")
        if shell_markers % 2 == 1: in_shell = not in_shell
        if in_shell or (shell_markers >= 2 and "writeShellScriptBin" in stripped): continue
        if "writeShellScriptBin" in stripped:
            skip_expr = stripped.count("(") - stripped.count(")"); continue
        if skip_expr > 0:
            skip_expr += stripped.count("(") - stripped.count(")"); continue
        if stripped.startswith("(") or "withPackages" in stripped: continue
        code = re.sub(r"#.*", "", stripped)
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9._-]*", code):
            if token not in _SKIP and len(token) > 1:
                pkgs.append(token)
    seen, result = set(), []
    for p in pkgs:
        if p not in seen:
            seen.add(p); result.append(p)
    return result


def _find_package(pkg_name: str) -> list[str]:
    candidates = []
    if os.path.isdir(HOSTS_DIR):
        for host in os.listdir(HOSTS_DIR):
            f = packages_list_path(host)
            if os.path.isfile(f) and pkg_name in _read_packages(f):
                candidates.append(f)
    if pkg_name in _read_packages(HOME_NIX):
        candidates.append(HOME_NIX)
    return candidates


def _insert_to_user_packages_nix(pkg_name: str, path: str) -> bool:
    """Insert a package attribute into the `with pkgs; [ ... ]` list (before closing `]`)."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        print(f"  ✗ Cannot read: {path}")
        return False

    insert_at = _find_with_pkgs_list_insert_line(lines)
    if insert_at is None:
        print(f"  ✗ with pkgs; [ … ] list not found in {path}")
        return False

    # Indent: match previous non-comment package line inside the list, else two spaces
    indent = "  "
    start = _find_with_pkgs_header_line(lines)
    if start is not None:
        for j in range(start + 1, insert_at):
            raw = lines[j]
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if raw.strip().startswith("]"):
                break
            indent = re.match(r"(\s*)", raw).group(1) or indent
            break

    _backup(path)
    lines.insert(insert_at, f"{indent}{pkg_name}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True


def _insert_to_file(pkg_name: str, path: str) -> bool:
    if os.path.basename(path) == "user-packages.nix":
        if not os.path.isfile(path):
            _create_user_packages_nix(path)
        return _insert_to_user_packages_nix(pkg_name, path)
    if not os.path.isfile(path):
        _create_packages_nix(path)
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        print(f"  ✗ Cannot read: {path}"); return False
    in_block = in_shell_block = False
    depth = 0
    insert_at = -1
    indent = "    "
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not in_block:
            if "home.packages" in stripped and "with pkgs" in stripped:
                in_block = True
                depth = stripped.count("[") - stripped.count("]"); continue
        else:
            depth += stripped.count("[") - stripped.count("]")
            sq = stripped.count("''")
            if sq % 2 == 1:
                in_shell_block = not in_shell_block
            if not in_shell_block and "writeShellScriptBin" not in stripped:
                code = re.sub(r"#.*", "", stripped)
                if re.search(r"[a-zA-Z]", code) and not stripped.startswith("("):
                    indent = re.match(r"(\s*)", line).group(1)
                    insert_at = i + 1
            if depth <= 0:
                if insert_at == -1: insert_at = i
                break
    if insert_at == -1:
        print(f"  ✗ home.packages block not found in {path}"); return False
    _backup(path)
    lines.insert(insert_at, f"{indent}{pkg_name}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True


def _remove_from_file(pkg_name: str, path: str) -> bool:
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return False
    new_lines, removed = [], False
    for line in lines:
        if re.sub(r"#.*", "", line).strip().rstrip(",") == pkg_name:
            removed = True
        else:
            new_lines.append(line)
    if not removed:
        print(f"  ✗ Line '{pkg_name}' not found"); return False
    _backup(path)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"  ✓ Removed: {pkg_name}")
    return True


def _create_user_packages_nix(path: str):
    """Create an empty user-packages.nix (list only)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    host = os.path.basename(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            f"# hosts/{host}/user-packages.nix — managed with nixctl pkg add/remove\n"
            f"# Close the list with `]` only (no semicolon after `]`).\n"
            f"{{ pkgs, ... }}:\n"
            f"with pkgs; [\n"
            f"]\n"
        )
    print(f"  ✓ Created: {path}")


def _create_packages_nix(path: str):
    """Create packages.nix (wrapper + nixctl from flake) and user-packages.nix."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    host = os.path.basename(os.path.dirname(path))
    up = os.path.join(os.path.dirname(path), "user-packages.nix")
    if not os.path.isfile(up):
        _create_user_packages_nix(up)
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            f"# hosts/{host}/packages.nix — managed by nixctl host; edit user-packages.nix for packages\n"
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
    print(f"  ✓ Created: {path}")


def _backup(path: str):
    import shutil
    shutil.copy2(path, path + ".bak")


def _maybe_rebuild():
    print()
    if confirm("Apply now? (nixctl sys rebuild)", default=False):
        from .sys import rebuild
        rebuild()
