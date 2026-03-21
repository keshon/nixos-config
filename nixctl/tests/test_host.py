"""
tests/test_host.py — host management and flake.nix generation
"""

import sys
import os
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


# ---------------------------------------------------------------------------
# Helpers to patch config paths into a tmp dir
# ---------------------------------------------------------------------------

def setup_nixos_dir(tmp_path):
    """Copy fixtures into a tmp nixos dir and patch config paths."""
    nixos = tmp_path / "nixos"
    nixos.mkdir()
    hosts = nixos / "hosts"
    hosts.mkdir()

    shutil.copy(os.path.join(FIXTURES, "flake.tmpl.nix"), nixos / "flake.tmpl.nix")
    (nixos / "flake.nix").write_text("")

    # Patch config module
    import importlib
    import modules.config as cfg
    cfg.NIXOS_DIR  = str(nixos)
    cfg.HOSTS_DIR  = str(hosts)
    cfg.FLAKE_NIX  = str(nixos / "flake.nix")
    cfg.FLAKE_TMPL = str(nixos / "flake.tmpl.nix")
    cfg.STORE_FILE = str(nixos / ".nixctl-store")

    # Reload host so it re-imports patched config constants
    import modules.host
    importlib.reload(modules.host)

    return nixos, hosts

# ---------------------------------------------------------------------------
# Flake rendering
# ---------------------------------------------------------------------------

class TestRenderFlake:
    def test_two_hosts_normal(self, tmp_path):
        nixos, hosts = setup_nixos_dir(tmp_path)
        from modules.host import _render_flake

        result = _render_flake({
            "desktop": {"env": "desktop", "hw": "desktop"},
            "laptop":  {"env": "laptop",  "hw": "laptop"},
        }, tmpl_path=str(nixos / "flake.tmpl.nix"))

        assert 'desktop = mkHost { env = "desktop"; hw = "desktop"; }' in result
        assert 'laptop = mkHost { env = "laptop"; hw = "laptop"; }' in result
        assert "__HOSTS__" not in result

    def test_cross_environment(self, tmp_path):
        nixos, hosts = setup_nixos_dir(tmp_path)
        from modules.host import _render_flake

        result = _render_flake({
            "desktop": {"env": "laptop", "hw": "desktop", "ref": "minimal"},
        }, tmpl_path=str(nixos / "flake.tmpl.nix"))

        assert 'env = "laptop"' in result
        assert 'hw = "desktop"' in result

    def test_nondefault_ref_rendered(self, tmp_path):
        nixos, hosts = setup_nixos_dir(tmp_path)
        from modules.host import _render_flake

        result = _render_flake({
            "desktop": {"env": "desktop", "hw": "desktop", "ref": "gaming"},
        }, tmpl_path=str(nixos / "flake.tmpl.nix"))

        assert 'ref = "gaming"' in result
        assert 'env = "desktop"' in result

    def test_hw_never_equals_other_machine(self, tmp_path):
        nixos, hosts = setup_nixos_dir(tmp_path)
        from modules.host import _render_flake, _update_flake_env

        # Simulate: host use laptop on desktop machine
        (hosts / "desktop").mkdir()
        (hosts / "laptop").mkdir()
        (nixos / "flake.nix").write_text(
            'nixosConfigurations = {\n'
            '  desktop = mkHost { env = "desktop"; hw = "desktop"; };\n'
            '  laptop  = mkHost { env = "laptop";  hw = "laptop"; };\n'
            '};\n'
        )

        _update_flake_env(machine="desktop", env="laptop")

        content = (nixos / "flake.nix").read_text()
        # hw must remain "desktop", not "laptop"
        assert 'hw = "desktop"' in content
        assert 'env = "laptop"' in content


# ---------------------------------------------------------------------------
# Host creation
# ---------------------------------------------------------------------------

class TestNewHost:
    def test_creates_host_nix(self, tmp_path, monkeypatch):
        nixos, hosts = setup_nixos_dir(tmp_path)
        from modules.host import _write_host_nix

        host_dir = hosts / "workstation"
        host_dir.mkdir()
        _write_host_nix("workstation", str(host_dir), bootloader="bios", device="/dev/sda")

        host = (host_dir / "host.nix").read_text()
        assert "nixos-workstation" in host
        assert "grub" not in host
        boot = (host_dir / "boot.nix").read_text()
        assert "grub.enable" in boot
        assert "grub.device" in boot
        assert "/dev/sda" in boot

    def test_creates_uefi_host_nix(self, tmp_path):
        nixos, hosts = setup_nixos_dir(tmp_path)
        from modules.host import _write_host_nix

        host_dir = hosts / "laptop"
        host_dir.mkdir()
        _write_host_nix("laptop", str(host_dir), bootloader="uefi")

        assert "nixos-laptop" in (host_dir / "host.nix").read_text()
        boot = (host_dir / "boot.nix").read_text()
        assert "systemd-boot" in boot
        assert "canTouchEfiVariables = true" in boot
        assert "grub" not in boot

    def test_creates_packages_nix(self, tmp_path):
        nixos, hosts = setup_nixos_dir(tmp_path)
        from modules.host import _write_packages_nix

        host_dir = hosts / "newhost"
        host_dir.mkdir()
        _write_packages_nix("newhost", str(host_dir))

        content = (host_dir / "packages.nix").read_text()
        assert "home.packages" in content
        assert "inputs.nixctl.packages" in content
        assert "user-packages.nix" in content
        up = (host_dir / "user-packages.nix").read_text()
        assert "with pkgs" in up
        assert "writeShellScriptBin" not in up

    def test_flake_updated_after_new(self, tmp_path, monkeypatch):
        nixos, hosts = setup_nixos_dir(tmp_path)

        # Pre-populate hosts/ so _current_hosts_config finds them via directory fallback
        (hosts / "desktop").mkdir()
        (hosts / "newhost").mkdir()

        from modules.host import _update_flake_add
        _update_flake_add("newhost")

        content = (nixos / "flake.nix").read_text()
        assert "newhost" in content
        assert "desktop" in content


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class TestStore:
    def test_save_and_load(self, tmp_path):
        nixos, hosts = setup_nixos_dir(tmp_path)
        from modules.config import save_store, load_store

        save_store({"host": "desktop", "machine": "desktop"})
        data = load_store()
        assert data["host"] == "desktop"
        assert data["machine"] == "desktop"

    def test_missing_store_returns_empty(self, tmp_path):
        nixos, hosts = setup_nixos_dir(tmp_path)
        from modules.config import load_store
        assert load_store() == {}

    def test_set_get_value(self, tmp_path):
        nixos, hosts = setup_nixos_dir(tmp_path)
        from modules.config import set_store_value, get_store_value

        set_store_value("host", "laptop")
        assert get_store_value("host") == "laptop"
        assert get_store_value("missing", "default") == "default"
