"""
tests/test_dconf.py — GVariant → Nix conversion

These are pure functions with no side effects — fast and reliable.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.dconf import convert_value, parse_dconf, section_to_nix, inject

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


# ---------------------------------------------------------------------------
# convert_value
# ---------------------------------------------------------------------------

class TestConvertValue:
    def test_bool_true(self):
        assert convert_value("true") == "true"

    def test_bool_false(self):
        assert convert_value("false") == "false"

    def test_int_normal(self):
        assert convert_value("42") == "42"

    def test_int_negative(self):
        assert convert_value("-1") == "-1"

    def test_int32_boundary(self):
        assert convert_value("2147483647") == "2147483647"
        assert convert_value("-2147483648") == "-2147483648"

    def test_int64_large(self):
        # The donation-reminder bug — large timestamp must use mkInt64
        result = convert_value("1773854363479992")
        assert result == "(lib.hm.gvariant.mkInt64 1773854363479992)"

    def test_int64_explicit_prefix(self):
        result = convert_value("int64 1773854363479992")
        assert result == "(lib.hm.gvariant.mkInt64 1773854363479992)"

    def test_uint32(self):
        result = convert_value("uint32 100")
        assert result == "(lib.hm.gvariant.mkUint32 100)"

    def test_float(self):
        assert convert_value("0.6") == "0.6"
        assert convert_value("0.59999999999999998") == "0.59999999999999998"

    def test_string(self):
        assert convert_value("'hello'") == '"hello"'

    def test_string_with_path(self):
        result = convert_value("'file:///home/user/wallpaper.jpg'")
        assert result == '"file:///home/user/wallpaper.jpg"'

    def test_empty_array(self):
        assert convert_value("@as []") == "[]"
        assert convert_value("@av []") == "[]"

    def test_string_array(self):
        result = convert_value("['firefox.desktop', 'nautilus.desktop']")
        assert '"firefox.desktop"' in result
        assert '"nautilus.desktop"' in result
        assert result.startswith("[ ")
        assert result.endswith(" ]")

    def test_xkb_tuple(self):
        result = convert_value("[('xkb', 'us'), ('xkb', 'ru')]")
        assert "mkTuple" in result
        assert '"us"' in result
        assert '"ru"' in result

    def test_gvariant_wrapper(self):
        # <'value'> should unwrap and convert inner value
        result = convert_value("<'default'>")
        assert result == '"default"'

    def test_color_string(self):
        result = convert_value("'#26a269'")
        assert result == '"#26a269"'


# ---------------------------------------------------------------------------
# parse_dconf
# ---------------------------------------------------------------------------

class TestParseDconf:
    def test_parse_fixture(self):
        path = os.path.join(FIXTURES, "dconf-backup.txt")
        sections = parse_dconf(path)
        assert len(sections) == 5

        paths = [s["path"] for s in sections]
        assert "org/gnome/desktop/interface" in paths
        assert "org/gnome/desktop/background" in paths

    def test_section_keys(self):
        path = os.path.join(FIXTURES, "dconf-backup.txt")
        sections = parse_dconf(path)
        iface = next(s for s in sections if "interface" in s["path"])
        keys = dict(iface["keys"])
        assert "clock-show-seconds" in keys
        assert "font-name" in keys

    def test_int64_key_parsed(self):
        path = os.path.join(FIXTURES, "dconf-backup.txt")
        sections = parse_dconf(path)
        housekeeping = next(s for s in sections if "housekeeping" in s["path"])
        keys = dict(housekeeping["keys"])
        assert "donation-reminder-last-shown" in keys
        assert "int64" in keys["donation-reminder-last-shown"]


# ---------------------------------------------------------------------------
# section_to_nix
# ---------------------------------------------------------------------------

class TestSectionToNix:
    def test_basic_output(self):
        section = {
            "path": "org/gnome/desktop/interface",
            "keys": [
                ("clock-show-seconds", "true"),
                ("font-name", "'SF Pro Display 11'"),
            ]
        }
        result = section_to_nix(section)
        assert '"org/gnome/desktop/interface" = {' in result
        assert "clock-show-seconds = true;" in result
        assert 'font-name = "SF Pro Display 11";' in result

    def test_int64_in_output(self):
        section = {
            "path": "org/gnome/settings-daemon/plugins/housekeeping",
            "keys": [("donation-reminder-last-shown", "int64 1773854363479992")]
        }
        result = section_to_nix(section)
        assert "mkInt64" in result
        assert "1773854363479992" in result


# ---------------------------------------------------------------------------
# inject
# ---------------------------------------------------------------------------

class TestInject:
    def test_inject_into_home_nix(self, tmp_path):
        home_nix = tmp_path / "home.nix"
        # Copy fixture
        import shutil
        shutil.copy(os.path.join(FIXTURES, "home.nix"), home_nix)

        nix_block = '    "org/gnome/desktop/interface" = {\n      clock-show-seconds = true;\n    };\n\n'
        inject(nix_block, str(home_nix))

        content = home_nix.read_text()
        assert "clock-show-seconds" in content
        assert "# DCONF_BEGIN" in content
        assert "# DCONF_END" in content

    def test_backup_created(self, tmp_path):
        home_nix = tmp_path / "home.nix"
        import shutil
        shutil.copy(os.path.join(FIXTURES, "home.nix"), home_nix)

        inject("", str(home_nix))
        assert (tmp_path / "home.nix.bak").exists()

    def test_missing_markers(self, tmp_path, capsys):
        home_nix = tmp_path / "home.nix"
        home_nix.write_text("{ }\n")  # no markers
        inject("some block", str(home_nix))
        captured = capsys.readouterr()
        assert "not found" in captured.out
