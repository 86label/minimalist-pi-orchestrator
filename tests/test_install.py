from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"


class InstallerTests(unittest.TestCase):
    def installer_env(self, home: Path, config: Path | None = None) -> dict[str, str]:
        fake_bin = home / "fake-bin"
        fake_bin.mkdir(exist_ok=True)
        for name in ("treehouse", "herdr", "pi"):
            executable = fake_bin / name
            executable.write_text("#!/bin/sh\nprintf '%s 99.0.0\\n' \"$(basename \"$0\")\"\n")
            executable.chmod(0o755)
        env = os.environ | {"HOME": str(home), "PATH": f"{fake_bin}:{os.environ['PATH']}"}
        if config is not None:
            env["XDG_CONFIG_HOME"] = str(config)
        return env

    def test_copy_install_is_isolated_idempotent_and_preserves_config(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            config = Path(temporary) / "config"
            home.mkdir()
            env = self.installer_env(home, config)
            command = ["bash", str(INSTALLER)]
            first = subprocess.run(command, env=env, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            launcher = home / ".local/bin/pi-worker"
            desk = home / ".local/bin/pi-desk"
            extension = home / ".pi/agent/extensions/minimalist-pi-orchestrator.ts"
            repos = config / "pi-worker/repos.json"
            self.assertTrue(launcher.is_file() and os.access(launcher, os.X_OK))
            self.assertTrue(desk.is_file() and os.access(desk, os.X_OK))
            self.assertTrue(extension.is_file())
            self.assertEqual(repos.stat().st_mode & 0o777, 0o600)
            repos.write_text('{"keep": true}\n')
            second = subprocess.run(command, env=env, text=True, capture_output=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(repos.read_text(), '{"keep": true}\n')
            self.assertIn("unchanged", second.stdout)

    def test_different_target_is_refused_without_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            target = home / ".local/bin/pi-worker"
            target.parent.mkdir(parents=True)
            target.write_text("different")
            env = self.installer_env(home)
            result = subprocess.run(["bash", str(INSTALLER)], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("--backup", result.stderr)
            self.assertEqual(target.read_text(), "different")


if __name__ == "__main__":
    unittest.main()
