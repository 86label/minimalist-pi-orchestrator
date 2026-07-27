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
if name == "gh" and args[:2] == ["pr", "list"]:
    print(os.environ.get("GH_PRS", "[]"))
    raise SystemExit(0)
if name == "treehouse":
    if args == ["status"]:
        if os.environ.get("TREEHOUSE_STATUS_WORKTREE"):
            print(f"1 leased {os.environ['TREEHOUSE_STATUS_WORKTREE']} (held by {os.environ.get('TREEHOUSE_STATUS_HOLDER', '')})")
        raise SystemExit(0)
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
        marker = os.environ.get("HERDR_RESTORE_MARKER")
        if os.environ.get("HERDR_LIVE") or (marker and Path(marker).exists()):
            print(json.dumps({"focused_workspace_id": "workspace-snapshot", "tabs": [{"workspace_id": "orchestrator-workspace", "tab_id": "worker-tab"}], "agents": [{"agent": os.environ.get("HERDR_AGENT", "pi"), "workspace_id": "orchestrator-workspace", "tab_id": os.environ.get("HERDR_AGENT_TAB", "worker-tab"), "pane_id": "worker-pane", "terminal_id": "term-1", "cwd": os.environ["HERDR_LIVE_CWD"], "agent_status": os.environ.get("HERDR_AGENT_STATUS", "idle"), "agent_session": {"agent": "pi", "source": "herdr:pi", "kind": os.environ.get("HERDR_SESSION_KIND", "path"), "value": os.environ.get("HERDR_SESSION_PATH", "")}}]}))
        else:
            print(json.dumps({"focused_workspace_id": "workspace-snapshot"}))
    elif args[:2] == ["tab", "create"]:
        print(json.dumps({"tab_id": "worker-tab", "pane_id": "worker-pane", "terminal_id": "term-1"}))
    elif args[:2] == ["pane", "get"]:
        print(json.dumps({"workspace_id": "orchestrator-workspace", "tab_id": "worker-tab", "pane_id": "worker-pane", "terminal_id": "term-1", "cwd": os.environ.get("HERDR_LIVE_CWD", "")}))
    elif args[:2] == ["pane", "read"]:
        print(os.environ.get("HERDR_PANE_OUTPUT", "recent useful output"))
    elif args[:2] in (["pane", "send-text"], ["pane", "send-keys"]):
        if args[:2] == ["pane", "send-keys"] and os.environ.get("HERDR_FAIL_ENTER"):
            print("Enter rejected", file=sys.stderr)
            raise SystemExit(9)
        print("ok")
    elif args[:2] == ["pane", "run"]:
        if os.environ.get("HERDR_RESTORE_MARKER") and "--session" in args[-1]:
            Path(os.environ["HERDR_RESTORE_MARKER"]).write_text("restored")
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
        for name in ("treehouse", "herdr", "pi", "gh"):
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
        self.env.pop("PI_WORKER_NAME", None)
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
        self.assertEqual(parsed[:4], ["pi", "--name", "Alpha worker", "--approve"])
        self.assertEqual(parsed[4:8], ["--session-dir", state["session_dir"], "--session-id", state["instance_id"]])
        self.assertEqual(parsed[8:], ["--model", "provider/model", prompt])
        self.assertTrue(state["prompted"])
        self.assertEqual(Path(state["session_dir"]).stat().st_mode & 0o777, 0o700)

    def test_empty_human_session_is_focused_and_status_is_durable(self) -> None:
        state = self.start("human", "--focus")
        create = next(c for c in self.commands() if c[:3] == ["herdr", "tab", "create"])
        self.assertIn("--focus", create)
        pane = next(c for c in self.commands() if c[:3] == ["herdr", "pane", "run"])
        parsed = shlex.split(pane[-1].removeprefix("exec "))
        self.assertEqual(parsed[:4], ["pi", "--name", "Alpha worker", "--approve"])
        self.assertEqual(parsed[4:], ["--session-dir", state["session_dir"], "--session-id", state["instance_id"]])
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
        self.assertEqual(stat.S_IMODE((self.state / "sessions").stat().st_mode), 0o700)

    def test_managed_worker_cannot_start_nested_worker_before_host_mutation(self) -> None:
        env = self.env | {"PI_WORKER_NAME": "parent-worker"}
        result = self.worker("start", "--name", "nested", env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot start nested workers", result.stderr)
        self.assertIn("ask the orchestrator", result.stderr)
        self.assertEqual(self.commands(), [])
        self.assertFalse(self.state.exists())

        # The same request from an orchestrator environment retains normal startup.
        state = self.start("sibling")
        self.assertEqual(state["name"], "sibling")
        self.assertTrue(any(c[:2] == ["treehouse", "get"] for c in self.commands()))

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
        transcript = Path(state["session_dir"]) / f"saved_{state['instance_id']}.jsonl"
        transcript.write_text('{"type":"session"}\n')
        refused = self.worker("return", "dirty")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("uncommitted changes", refused.stderr)
        self.assertTrue((self.state / "workers/dirty.json").exists())
        returned = self.worker("return", "dirty", "--force")
        self.assertEqual(returned.returncode, 0, returned.stderr)
        payload = json.loads(returned.stdout)
        self.assertEqual(payload["diagnostics"]["disposition"], "dirty")
        self.assertEqual(payload["session_retained"], str(transcript))
        self.assertTrue(transcript.is_file())
        branch = run(["git", "-C", str(self.repo), "branch", "--list", state["branch"]]).stdout.strip()
        self.assertIn(state["branch"], branch)

    def test_return_treats_unbound_pr_head_as_ambiguous(self) -> None:
        state = self.start("pr-identity")
        (Path(state["worktree"]) / "pr.txt").write_text("commit\n")
        run(["git", "-C", state["worktree"], "add", "pr.txt"])
        run(["git", "-C", state["worktree"], "commit", "-m", "worker commit"])
        run(["git", "-C", str(self.repo), "remote", "set-url", "origin", "git@github.com:owner/app.git"])
        head = run(["git", "-C", state["worktree"], "rev-parse", "HEAD"]).stdout.strip()
        wrong = [{"number": 1, "state": "OPEN", "headRefName": state["branch"], "headRefOid": "wrong", "headRepository": {"nameWithOwner": "fork/app"}}]
        result = self.worker("return", "pr-identity", env=self.env | {"GH_PRS": json.dumps(wrong)})
        self.assertEqual(result.returncode, 0, result.stderr)
        diagnostics = json.loads(result.stdout)["diagnostics"]
        self.assertEqual(diagnostics["disposition"], "ambiguous")
        self.assertEqual(diagnostics["pull_requests"]["status"], "ambiguous")
        self.assertNotEqual(head, "wrong")

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

    def test_exact_inspection_follow_up_and_missing_resume_are_conservative(self) -> None:
        state = self.start("aware")
        session = self.root / "exact-session.jsonl"
        session.write_text('{"type":"session"}\n')
        env = self.env | {
            "HERDR_LIVE": "1", "HERDR_LIVE_CWD": state["worktree"],
            "HERDR_SESSION_PATH": str(session), "HERDR_AGENT_STATUS": "blocked",
            "HERDR_PANE_OUTPUT": "need a decision\n" + ("x" * 9000),
        }
        incomplete = self.worker("inspect", "aware", env=env | {"HERDR_SESSION_KIND": "id"})
        self.assertEqual(incomplete.returncode, 0, incomplete.stderr)
        self.assertEqual(json.loads(incomplete.stdout)["classification"], "ambiguous")
        self.assertNotIn("session_path", json.loads((self.state / "workers/aware.json").read_text()))
        inspected = self.worker("inspect", "aware", env=env)
        self.assertEqual(inspected.returncode, 0, inspected.stderr)
        report = json.loads(inspected.stdout)
        self.assertEqual(report["classification"], "blocked")
        self.assertLessEqual(len(report["recent_output"]), 8000)
        self.assertEqual(json.loads((self.state / "workers/aware.json").read_text())["session_path"], str(session))
        self.assertEqual(report["herdr"]["session_path"], str(session))
        followed = self.worker("follow-up", "aware", "Please choose A or B.", env=env)
        self.assertEqual(followed.returncode, 0, followed.stderr)
        sends = [c for c in self.commands() if c[:3] == ["herdr", "pane", "send-keys"]]
        self.assertEqual(sends[-1], ["herdr", "pane", "send-keys", "worker-pane", "enter"])
        self.assertEqual(json.loads(followed.stdout)["verification"], "inconclusive")
        enter_failed = self.worker("follow-up", "aware", "do not retry", env=env | {"HERDR_FAIL_ENTER": "1"})
        self.assertNotEqual(enter_failed.returncode, 0)
        self.assertIn("Enter rejected", enter_failed.stderr)
        self.assertEqual(len([c for c in self.commands() if c[:3] == ["herdr", "pane", "send-keys"]]), 2)
        cross_wired = self.worker("follow-up", "aware", "unsafe", env=env | {"HERDR_AGENT": "shell", "HERDR_AGENT_TAB": "other-tab"})
        self.assertNotEqual(cross_wired.returncode, 0)
        self.assertEqual(len([c for c in self.commands() if c[:3] == ["herdr", "pane", "send-text"]]), 2)
        missing = self.worker("resume", "aware", env=self.env)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("not an exact missing", missing.stderr)

    def test_restore_all_recreates_missing_worker_from_deterministic_session(self) -> None:
        state = self.start("durable")
        session = Path(state["session_dir"]) / f"2026-01-01T00-00-00Z_{state['instance_id']}.jsonl"
        session.write_text('{"type":"session"}\n')
        marker = self.root / "restored.marker"
        env = self.env | {
            "TREEHOUSE_STATUS_WORKTREE": state["worktree"],
            "TREEHOUSE_STATUS_HOLDER": "durable",
            "HERDR_RESTORE_MARKER": str(marker),
            "HERDR_LIVE_CWD": state["worktree"],
            "HERDR_SESSION_PATH": str(session),
            "HERDR_AGENT_STATUS": "idle",
        }
        restored = self.worker("restore-all", env=env)
        self.assertEqual(restored.returncode, 0, restored.stderr)
        result = json.loads(restored.stdout)
        self.assertEqual(result["restored"], ["durable"])
        self.assertEqual(result["already_live"], [])
        updated = json.loads((self.state / "workers/durable.json").read_text())
        self.assertEqual(updated["session_path"], str(session))
        launches = [c for c in self.commands() if c[:3] == ["herdr", "pane", "run"]]
        self.assertEqual(
            shlex.split(launches[-1][-1].removeprefix("exec ")),
            ["pi", "--approve", "--session", str(session)],
        )

    def test_unique_branch_after_return(self) -> None:
        first = self.start("repeat")
        self.assertEqual(self.worker("return", "repeat").returncode, 0)
        second = self.start("repeat")
        self.assertEqual(first["branch"], "work/repeat")
        self.assertEqual(second["branch"], "work/repeat-2")


if __name__ == "__main__":
    unittest.main()
