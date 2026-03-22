"""
tests/test_pkg.py — package list parsing and file manipulation
"""

import sys
import os
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.pkg import (
    _read_packages,
    _insert_to_file,
    _insert_chosen_packages,
    _remove_from_file,
    _match_rank,
    _filter,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestSearchRank:
    def test_exact_beats_prefix(self):
        index = [("go", "desc"), ("golang", "other")]
        out = _filter(index, "go")
        assert out[0][0] == "go"

    def test_match_rank_levels(self):
        assert _match_rank("go", "", "go") == 0
        assert _match_rank("golang", "", "go") == 1
        assert _match_rank("not-go", "", "go") == 2  # token boundary after '-'
        assert _match_rank("somethinggo", "", "go") == 3  # plain substring


class TestReadPackages:
    def test_reads_user_packages_nix(self):
        path = os.path.join(FIXTURES, "user-packages.nix")
        pkgs = _read_packages(path)
        assert "firefox" in pkgs
        assert "vlc" in pkgs
        assert "discord" in pkgs

    def test_reads_real_packages(self):
        path = os.path.join(FIXTURES, "packages.nix")
        pkgs = _read_packages(path)
        assert "firefox" in pkgs
        assert "vlc" in pkgs
        assert "discord" in pkgs

    def test_skips_writeshellscriptbin(self):
        # The bug: nixctl wrapper contents were leaking into pkg list
        path = os.path.join(FIXTURES, "packages.nix")
        pkgs = _read_packages(path)
        assert "HOME" not in pkgs
        assert "cd" not in pkgs
        assert "nixctl.py" not in pkgs
        assert "nixos" not in pkgs

    def test_skips_keywords(self):
        path = os.path.join(FIXTURES, "packages.nix")
        pkgs = _read_packages(path)
        assert "pkgs" not in pkgs
        assert "with" not in pkgs
        assert "home" not in pkgs

    def test_empty_file(self, tmp_path):
        f = tmp_path / "packages.nix"
        f.write_text("{ pkgs, ... }:\n{\n  home.packages = with pkgs; [\n  ];\n}\n")
        assert _read_packages(str(f)) == []

    def test_nonexistent_file(self, tmp_path):
        assert _read_packages(str(tmp_path / "missing.nix")) == []

    def test_no_duplicates(self, tmp_path):
        f = tmp_path / "packages.nix"
        f.write_text("{ pkgs, ... }:\n{\n  home.packages = with pkgs; [\n    vlc\n    vlc\n  ];\n}\n")
        pkgs = _read_packages(str(f))
        assert pkgs.count("vlc") == 1


class TestInsertPackage:
    def test_inserts_package(self, tmp_path):
        src = os.path.join(FIXTURES, "packages.nix")
        dst = tmp_path / "packages.nix"
        shutil.copy(src, dst)

        _insert_to_file("google-chrome", str(dst))

        pkgs = _read_packages(str(dst))
        assert "google-chrome" in pkgs

    def test_does_not_insert_inside_wrapper(self, tmp_path):
        # Core regression: package must NOT end up inside writeShellScriptBin block
        src = os.path.join(FIXTURES, "packages.nix")
        dst = tmp_path / "packages.nix"
        shutil.copy(src, dst)

        _insert_to_file("google-chrome", str(dst))

        content = dst.read_text()
        # The package should appear as a standalone line, not inside ''...''
        lines = content.splitlines()
        shell_block = False
        for line in lines:
            if "''" in line and "writeShellScriptBin" in line:
                shell_block = True
            if shell_block and "''" in line and "writeShellScriptBin" not in line:
                shell_block = False
            if shell_block and "google-chrome" in line:
                raise AssertionError("google-chrome was inserted inside writeShellScriptBin block!")

    def test_creates_backup(self, tmp_path):
        src = os.path.join(FIXTURES, "packages.nix")
        dst = tmp_path / "packages.nix"
        shutil.copy(src, dst)

        _insert_to_file("htop", str(dst))
        assert (tmp_path / "packages.nix.bak").exists()

    def test_insert_then_read(self, tmp_path):
        src = os.path.join(FIXTURES, "packages.nix")
        dst = tmp_path / "packages.nix"
        shutil.copy(src, dst)

        _insert_to_file("neovim", str(dst))
        pkgs = _read_packages(str(dst))
        assert "neovim" in pkgs
        # Original packages still present
        assert "firefox" in pkgs
        assert "vlc" in pkgs

    def test_inserts_user_packages_before_close(self, tmp_path):
        src = os.path.join(FIXTURES, "user-packages.nix")
        dst = tmp_path / "user-packages.nix"
        shutil.copy(src, dst)
        _insert_to_file("go", str(dst))
        text = dst.read_text()
        assert "with pkgs; [" in text
        assert text.find("go") < text.rfind("]")
        assert text.count("go") == 1

    def test_chosen_dedupes_identical_names(self, tmp_path):
        src = os.path.join(FIXTURES, "user-packages.nix")
        dst = tmp_path / "user-packages.nix"
        shutil.copy(src, dst)
        _insert_chosen_packages(
            [("go", "desc a"), ("go", "desc b"), ("go", "desc c")],
            str(dst),
        )
        assert _read_packages(str(dst)).count("go") == 1


class TestRemovePackage:
    def test_removes_package(self, tmp_path):
        src = os.path.join(FIXTURES, "packages.nix")
        dst = tmp_path / "packages.nix"
        shutil.copy(src, dst)

        result = _remove_from_file("vlc", str(dst))
        assert result is True
        assert "vlc" not in _read_packages(str(dst))

    def test_keeps_other_packages(self, tmp_path):
        src = os.path.join(FIXTURES, "packages.nix")
        dst = tmp_path / "packages.nix"
        shutil.copy(src, dst)

        _remove_from_file("vlc", str(dst))
        pkgs = _read_packages(str(dst))
        assert "firefox" in pkgs
        assert "discord" in pkgs

    def test_returns_false_for_missing(self, tmp_path):
        src = os.path.join(FIXTURES, "packages.nix")
        dst = tmp_path / "packages.nix"
        shutil.copy(src, dst)

        result = _remove_from_file("nonexistent-pkg", str(dst))
        assert result is False

    def test_insert_then_remove(self, tmp_path):
        src = os.path.join(FIXTURES, "packages.nix")
        dst = tmp_path / "packages.nix"
        shutil.copy(src, dst)

        _insert_to_file("htop", str(dst))
        assert "htop" in _read_packages(str(dst))

        _remove_from_file("htop", str(dst))
        assert "htop" not in _read_packages(str(dst))
