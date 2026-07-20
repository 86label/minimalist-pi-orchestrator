from __future__ import annotations

import json
import os
import shlex
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin/pi-worker"

FAKE = r'''#!/usr/bin/env python3
import json, os, subprocess, sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
log = Path(os.environ["FAKE_LOG"])
with log.open("a") as handle:
    handle.write(json.dumps([name, *args]) + "\n")
if args == ["--version"]:
    versions = {"treehouse": "2.0.1", "herdr": "0.7.4", "pi": "0.80.10"}
    version = os.environ.get(f"FAKE_{name.upper()}_VERSION", versions[name])
    print(f"{name} {version}")
    raise SystemExit(0)
if name == "pi":
    raise SystemExit(0)
if name == "treehouse":
    if args[:2] == ["get", "--lease"]:
        if os.environ.get("TREEHOUSE_PRIMARY"):
            print(Path.cwd())
            raise SystemExit(0)
        target = Path(os.environ["FAKE_WORKTREES"]) / args[-1]
        revision = os.environ.get("TREEHOUSE_REV", "refs/remotes/origin/main")
        result = subprocess.run(
            ["git", "-C", str(Path.cwd()), "worktree", "add", "--detach", str(target), revision],
            text=True, capture_output=True,
        )
        if result.returncode:
            print(result.stderr, file=sys.stderr)
            raise SystemExit(result.returncode)
        print(target)
        raise SystemExit(0)
    if args and args[0] == "return":
        target = Path(args[1])
        if not target.exists():
            raise SystemExit(0)
        git_dir = subprocess.run(["git", "-C", str(target), "rev-parse", "--absolute-git-dir"], text=True, capture_output=True).stdout.strip()
        common = subprocess.run(["git", "-C", str(target), "rev-parse", "--path-format=absolute", "--git-common-dir"], text=True, capture_output=True).stdout.strip()
        if git_dir == common:  # Never remove a primary checkout in a validation test.
            raise SystemExit(0)
        primary = Path(common).parent
        command = ["git", "-C", str(primary), "worktree", "remove", str(target)]
        if "--force" in args:
            command.append("--force")
        raise SystemExit(subprocess.run(command).returncode)
if name == "herdr":
    if args[:2] == ["api", "snapshot"]:
        print(json.dumps({"focused_workspace_id": "workspace-snapshot"}))
    elif args[:2] == ["tab", "create"]:
        print(json.dumps({"tab_id": "worker-tab", "pane_id": "worker-pane", "terminal_id": "term-1"}))
    elif args[:2] == ["pane", "run"]:
        if os.environ.get("HERDR_FAIL_PANE"):
            print("launch failed", file=sys.stderr)
            raise SystemExit(9)
        print("ok")
    elif args[:2] == ["tab", "get"]:
        print(json.dumps({"pane_count": int(os.environ.get("HERDR_PANE_COUNT", "1"))}))
    else:
        print("ok")
    raise SystemExit(0)
print("unsupported fake command", file=sys.stderr)
raise SystemExit(2)
'''


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=True)


class PiWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        self.seed = self.root / "seed"
        self.repo = self.root / "repo"
        run(["git", "init", "--bare", str(self.remote)])
        run(["git", "init", "-b", "main", str(self.seed)])
        run(["git", "-C", str(self.seed), "config", "user.name", "Test"])
        run(["git", "-C", str(self.seed), "config", "user.email", "test@example.invalid"])
        (self.seed / "README.md").write_text("base\n")
        run(["git", "-C", str(self.seed), "add", "README.md"])
        run(["git", "-C", str(self.seed), "commit", "-m", "base"])
        run(["git", "-C", str(self.seed), "remote", "add", "origin", str(self.remote)])
        run(["git", "-C", str(self.seed), "push", "-u", "origin", "main"])
        run(["git", "clone", "--branch", "main", str(self.remote), str(self.repo)])
        run(["git", "-C", str(self.repo), "config", "user.name", "Test"])
        run(["git", "-C", str(self.repo), "config", "user.email", "test@example.invalid"])

        self.bin = self.root / "fake-bin"
        self.bin.mkdir()
        fake = self.bin / "fake"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        for name in ("treehouse", "herdr", "pi"):
            (self.bin / name).symlink_to(fake)
        self.config = self.root / "repos.json"
        self.config.write_text(json.dumps({
            "default_repository": "app",
            "repositories": {
                "app": {"path": str(self.repo), "remote": "origin", "default_branch": "main"}
            },
        }))
        self.state = self.root / "state"
        self.log = self.root / "commands.jsonl"
        self.env = os.environ.copy()
        self.env.update({
            "PATH": f"{self.bin}:{self.env['PATH']}",
            "PI_WORKER_CONFIG": str(self.config),
            "PI_WORKER_STATE_DIR": str(self.state),
            "FAKE_LOG": str(self.log),
            "FAKE_WORKTREES": str(self.root / "worktrees"),
            "HERDR_WORKSPACE_ID": "orchestrator-workspace",
        })

    def tearDown(self) -> None:
        self.temp.cleanup()

    def worker(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(LAUNCHER), *args], text=True, capture_output=True,
            env=env or self.env,
        )

    def commands(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def start(self, name: str = "alpha", *extra: str) -> dict:
        result = self.worker("start", "--name", name, "--label", "Alpha worker", *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_explicit_tab_regression_and_quoted_delegated_prompt(self) -> None:
        prompt = "Fix user's 'quoted' thing; echo $HOME && touch /tmp/nope"
        state = self.start("alpha", "--prompt", prompt, "--model", "provider/model", "--no-focus")
        commands = self.commands()
        self.assertTrue(any(c[:3] == ["herdr", "tab", "create"] for c in commands))
        self.assertFalse(any(c[:3] == ["herdr", "agent", "start"] for c in commands))
        self.assertIn(
            ["treehouse", "get", "--lease", "--lease-holder", "alpha"], commands
        )
        create = next(c for c in commands if c[:3] == ["herdr", "tab", "create"])
        self.assertIn("--no-focus", create)
        pane = next(c for c in commands if c[:3] == ["herdr", "pane", "run"])
        parsed = shlex.split(pane[-1].removeprefix("exec "))
        self.assertEqual(parsed, ["pi", "--name", "Alpha worker", "--approve", "--model", "provider/model", prompt])
        self.assertTrue(state["prompted"])

    def test_empty_human_session_is_focused_and_status_is_durable(self) -> None:
        state = self.start("human", "--focus")
        create = next(c for c in self.commands() if c[:3] == ["herdr", "tab", "create"])
        self.assertIn("--focus", create)
        pane = next(c for c in self.commands() if c[:3] == ["herdr", "pane", "run"])
        self.assertEqual(shlex.split(pane[-1].removeprefix("exec ")), ["pi", "--name", "Alpha worker", "--approve"])
        status = self.worker("status")
        self.assertEqual(status.returncode, 0)
        self.assertEqual(json.loads(status.stdout)["workers"][0]["branch"], state["branch"])

    def test_dependency_minimum_is_enforced_before_lease(self) -> None:
        env = self.env | {"FAKE_PI_VERSION": "0.80.9"}
        result = self.worker("start", "--name", "old-pi", env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pi 0.80.9 is unsupported", result.stderr)
        self.assertFalse(any(c[:2] == ["treehouse", "get"] for c in self.commands()))

    def test_worker_state_is_owner_only(self) -> None:
        self.start("private-state")
        record = self.state / "workers/private-state.json"
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(record.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(record.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.state / "state.lock").stat().st_mode), 0o600)

    def test_default_allowlist_and_fetch_failure_is_closed(self) -> None:
        result = self.worker("start", "--name", "unknown", "--repo", "not-allowed")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown repository", result.stderr)
        config = json.loads(self.config.read_text())
        config["repositories"]["app"]["default_branch"] = "missing"
        self.config.write_text(json.dumps(config))
        result = self.worker("start", "--name", "fetch-fails")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unable to fetch", result.stderr)
        self.assertFalse(any(c[:2] == ["treehouse", "get"] for c in self.commands()))

    def test_primary_checkout_is_rejected(self) -> None:
        env = self.env | {"TREEHOUSE_PRIMARY": "1"}
        result = self.worker("start", "--name", "unsafe", env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to use the primary checkout", result.stderr)
        self.assertFalse(any(c[:2] == ["treehouse", "return"] for c in self.commands()))
        self.assertTrue(self.repo.exists())
        self.assertFalse((self.state / "workers/unsafe.json").exists())

    def test_worktree_must_match_fresh_fetched_base(self) -> None:
        (self.repo / "local-only.txt").write_text("ahead\n")
        run(["git", "-C", str(self.repo), "add", "local-only.txt"])
        run(["git", "-C", str(self.repo), "commit", "-m", "local only"])
        env = self.env | {"TREEHOUSE_REV": "HEAD"}
        result = self.worker("start", "--name", "stale", env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match fresh base", result.stderr)
        self.assertFalse(any(c[:3] == ["herdr", "tab", "create"] for c in self.commands()))

    def test_failed_launch_rolls_back_only_created_tab_lease_and_branch(self) -> None:
        env = self.env | {"HERDR_FAIL_PANE": "1"}
        result = self.worker("start", "--name", "rollback", env=env)
        self.assertNotEqual(result.returncode, 0)
        commands = self.commands()
        self.assertIn(["herdr", "tab", "close", "worker-tab"], commands)
        self.assertTrue(any(c[:2] == ["treehouse", "return"] and "--force" in c for c in commands))
        branch = run(["git", "-C", str(self.repo), "branch", "--list", "work/rollback"]).stdout.strip()
        self.assertEqual(branch, "")
        self.assertFalse((self.state / "workers/rollback.json").exists())

    def test_dirty_return_requires_explicit_force_and_branch_survives(self) -> None:
        state = self.start("dirty")
        (Path(state["worktree"]) / "untracked.txt").write_text("dirty")
        refused = self.worker("return", "dirty")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("uncommitted changes", refused.stderr)
        self.assertTrue((self.state / "workers/dirty.json").exists())
        returned = self.worker("return", "dirty", "--force")
        self.assertEqual(returned.returncode, 0, returned.stderr)
        branch = run(["git", "-C", str(self.repo), "branch", "--list", state["branch"]]).stdout.strip()
        self.assertIn(state["branch"], branch)

    def test_legacy_worker_in_callers_orchestrator_tab_closes_only_pane(self) -> None:
        self.start("legacy")
        record = self.state / "workers/legacy.json"
        state = json.loads(record.read_text())
        state["tab_id"] = "orchestrator-tab"
        state["pane_id"] = "legacy-worker-pane"
        record.write_text(json.dumps(state))
        env = self.env | {"HERDR_TAB_ID": "orchestrator-tab", "HERDR_PANE_ID": "orchestrator-pane"}
        result = self.worker("return", "legacy", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.commands()
        self.assertIn(["herdr", "pane", "close", "legacy-worker-pane"], commands)
        self.assertNotIn(["herdr", "tab", "close", "orchestrator-tab"], commands)

    def test_unique_branch_after_return(self) -> None:
        first = self.start("repeat")
        self.assertEqual(self.worker("return", "repeat").returncode, 0)
        second = self.start("repeat")
        self.assertEqual(first["branch"], "work/repeat")
        self.assertEqual(second["branch"], "work/repeat-2")


if __name__ == "__main__":
    unittest.main()
