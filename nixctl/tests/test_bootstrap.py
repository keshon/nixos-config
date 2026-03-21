"""
tests/test_bootstrap.py — bootstrap wizard (existing vs new host) with mocked I/O
"""

import sys
import os
import shutil
import importlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def setup_bootstrap_env(tmp_path):
    """Tmp nixos tree + patch config; reload host, reference, bootstrap."""
    nixos = tmp_path / "nixos"
    nixos.mkdir()
    hosts = nixos / "hosts"
    hosts.mkdir()
    refs = nixos / "references" / "minimal"
    refs.mkdir(parents=True)
    shutil.copy(
        os.path.join(FIXTURES, "references", "minimal", "home.nix"),
        refs / "home.nix",
    )

    shutil.copy(os.path.join(FIXTURES, "flake.tmpl.nix"), nixos / "flake.tmpl.nix")
    (nixos / "flake.nix").write_text("")

    import modules.config as cfg

    cfg.NIXOS_DIR = str(nixos)
    cfg.HOSTS_DIR = str(hosts)
    cfg.FLAKE_NIX = str(nixos / "flake.nix")
    cfg.FLAKE_TMPL = str(nixos / "flake.tmpl.nix")
    cfg.STORE_FILE = str(nixos / ".nixctl-store")
    cfg.REFERENCES_DIR = str(nixos / "references")

    import modules.host
    import modules.reference
    import modules.bootstrap

    importlib.reload(modules.host)
    importlib.reload(modules.reference)
    importlib.reload(modules.bootstrap)

    return nixos, hosts


def _noop_ok(*args, **kwargs):
    return True


def _noop_ok_host(host):
    return True


def _noop_flathub():
    pass


class TestBootstrapExisting:
    def test_writes_store_after_finalize(self, tmp_path, monkeypatch):
        nixos, hosts = setup_bootstrap_env(tmp_path)
        (hosts / "desktop").mkdir()

        monkeypatch.setattr("modules.bootstrap._copy_hardware", _noop_ok_host)
        monkeypatch.setattr("modules.bootstrap._link_etc", lambda: True)
        monkeypatch.setattr("modules.bootstrap._rebuild", _noop_ok_host)
        monkeypatch.setattr("modules.bootstrap._flathub", _noop_flathub)

        inputs = iter(["1", ""])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

        import modules.bootstrap

        modules.bootstrap.run([])

        from modules.config import load_store

        assert load_store().get("machine") == "desktop"
        assert load_store().get("host") == "desktop"
        assert load_store().get("created")


class TestBootstrapNewFromRef:
    def test_creates_host_and_flake(self, tmp_path, monkeypatch):
        nixos, hosts = setup_bootstrap_env(tmp_path)

        monkeypatch.setattr("modules.bootstrap._copy_hardware", _noop_ok_host)
        monkeypatch.setattr("modules.bootstrap._link_etc", lambda: True)
        monkeypatch.setattr("modules.bootstrap._rebuild", _noop_ok_host)
        monkeypatch.setattr("modules.bootstrap._flathub", _noop_flathub)
        monkeypatch.setattr(
            "modules.bootstrap._ask_bootloader",
            lambda dry_run=False: ("bios", "/dev/sda"),
        )
        monkeypatch.setattr(
            "modules.bootstrap.confirm",
            lambda q, default=False: True,
        )

        inputs = iter(["2", "1", "newbox"])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

        import modules.bootstrap

        modules.bootstrap.run([])

        assert (host_dir := nixos / "hosts" / "newbox").is_dir()
        assert (host_dir / "host.nix").is_file()
        assert "newbox" in (nixos / "flake.nix").read_text()

        from modules.config import load_store

        assert load_store().get("machine") == "newbox"
        assert load_store().get("host") == "newbox"
        assert load_store().get("created")

    def test_name_collision_aborts(self, tmp_path, monkeypatch, capsys):
        nixos, hosts = setup_bootstrap_env(tmp_path)
        (hosts / "desktop").mkdir()

        monkeypatch.setattr("modules.bootstrap._copy_hardware", _noop_ok_host)
        monkeypatch.setattr("modules.bootstrap._link_etc", lambda: True)
        monkeypatch.setattr("modules.bootstrap._rebuild", _noop_ok_host)
        monkeypatch.setattr("modules.bootstrap._flathub", _noop_flathub)
        monkeypatch.setattr(
            "modules.bootstrap._ask_bootloader",
            lambda dry_run=False: ("bios", "/dev/sda"),
        )
        monkeypatch.setattr(
            "modules.bootstrap.confirm",
            lambda q, default=False: True,
        )

        inputs = iter(["2", "1", "desktop"])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

        import modules.bootstrap

        modules.bootstrap.run([])

        out = capsys.readouterr().out
        assert "already exists" in out or "already" in out.lower()


class TestResolveReferenceList:
    def test_no_refs_no_fallback_returns_none(self, tmp_path):
        nixos, hosts = setup_bootstrap_env(tmp_path)
        import shutil as sh

        sh.rmtree(nixos / "references")

        import modules.config as cfg

        cfg.REFERENCES_DIR = str(nixos / "references")

        import modules.reference
        import modules.bootstrap

        importlib.reload(modules.reference)
        importlib.reload(modules.bootstrap)

        os.makedirs(nixos / "references", exist_ok=True)

        import modules.bootstrap as boot

        assert boot._resolve_reference_list() is None
