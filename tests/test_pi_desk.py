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
DESK = ROOT / "bin/pi-desk"

FAKE = r'''#!/usr/bin/env python3
import json, os, shlex, sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
log = Path(os.environ["FAKE_LOG"])
with log.open("a") as handle:
    handle.write(json.dumps([name, *args]) + "\n")
if name == "treehouse" and args == ["status"]:
    leases = json.loads(Path(os.environ["FAKE_LEASES"]).read_text())
    for index, (path, holder) in enumerate(leases.items(), 1):
        print(f"{index}     leased       {path}  (held by {holder})")
    raise SystemExit(0)
if name != "herdr":
    print("unsupported fake", file=sys.stderr)
    raise SystemExit(2)
snapshot_path = Path(os.environ["HERDR_SNAPSHOT_FILE"])
def load(): return json.loads(snapshot_path.read_text())
def save(value): snapshot_path.write_text(json.dumps(value))
def option(flag): return args[args.index(flag) + 1]
def new_ids(value):
    counter = int(value.get("_counter", 0)) + 1
    value["_counter"] = counter
    return f"desk-w{counter}", f"desk-t{counter}", f"desk-p{counter}", f"desk-term{counter}"
def add_agent(value, pane, info, session, cwd=None):
    value["agents"] = [a for a in value["agents"] if a.get("pane_id") != pane]
    value["agents"].append({
        "agent": "pi", "agent_status": "idle", "cwd": cwd or info["cwd"],
        "workspace_id": info["workspace_id"], "tab_id": info["tab_id"],
        "pane_id": pane, "terminal_id": info["terminal_id"], "focused": False,
        "agent_session": {"agent": "pi", "kind": "path", "source": "herdr:pi", "value": session},
    })
def add_starting_agent(value, pane, info):
    value["agents"] = [a for a in value["agents"] if a.get("pane_id") != pane]
    value["agents"].append({
        "agent": "pi", "agent_status": "unknown", "cwd": info["cwd"],
        "workspace_id": info["workspace_id"], "tab_id": info["tab_id"],
        "pane_id": pane, "terminal_id": info["terminal_id"], "focused": False,
    })
if args[:2] == ["api", "snapshot"]:
    value = load()
    pending = value.setdefault("_pending", {})
    for pane, item in list(pending.items()):
        item["remaining"] -= 1
        if item["remaining"] <= 0:
            add_agent(value, pane, item["info"], item["session"])
            pending.pop(pane)
    save(value)
    visible = json.loads(json.dumps(value))
    visible.pop("_created", None)
    visible.pop("_counter", None)
    visible.pop("_pending", None)
    visible.pop("_starting", None)
    print(json.dumps({"result": {"snapshot": visible}}))
    raise SystemExit(0)
value = load()
created = value.setdefault("_created", {})
if args[:2] == ["workspace", "create"]:
    workspace, tab, pane, terminal = new_ids(value)
    cwd = option("--cwd")
    label = option("--label")
    value["workspaces"].append({"workspace_id": workspace, "label": label, "number": 1, "focused": False})
    value["tabs"].append({"workspace_id": workspace, "tab_id": tab, "label": "Shell", "number": 1, "pane_count": 1, "focused": False})
    created[pane] = {"workspace_id": workspace, "tab_id": tab, "terminal_id": terminal, "cwd": cwd, "label": "Shell"}
    save(value)
    print(json.dumps({"workspace_id": workspace, "tab_id": tab, "pane_id": pane, "terminal_id": terminal}))
    raise SystemExit(0)
if args[:2] == ["tab", "create"]:
    workspace, tab, pane, terminal = new_ids(value)
    workspace = option("--workspace")
    cwd = option("--cwd")
    label = option("--label")
    number = 1 + max([t.get("number", 0) for t in value["tabs"] if t.get("workspace_id") == workspace] or [0])
    value["tabs"].append({"workspace_id": workspace, "tab_id": tab, "label": label, "number": number, "pane_count": 1, "focused": False})
    created[pane] = {"workspace_id": workspace, "tab_id": tab, "terminal_id": terminal, "cwd": cwd, "label": label}
    save(value)
    print(json.dumps({"workspace_id": workspace, "tab_id": tab, "pane_id": pane, "terminal_id": terminal}))
    raise SystemExit(0)
if args[:2] == ["tab", "rename"]:
    tab, label = args[2], args[3]
    for item in value["tabs"]:
        if item.get("tab_id") == tab: item["label"] = label
    for item in created.values():
        if item["tab_id"] == tab: item["label"] = label
    save(value)
    print("ok")
    raise SystemExit(0)
if args[:2] == ["pane", "run"]:
    pane, command = args[2], args[3]
    info = created[pane]
    fail_labels = set(filter(None, os.environ.get("HERDR_FAIL_LABELS", "").split(",")))
    if info["label"] == os.environ.get("HERDR_FAIL_LABEL") or info["label"] in fail_labels:
        print("configured pane failure", file=sys.stderr)
        raise SystemExit(9)
    parsed = shlex.split(command.removeprefix("exec "))
    session = parsed[parsed.index("--session") + 1]
    if info["label"] == os.environ.get("HERDR_NEVER_LABEL"):
        save(value)
        print("submitted")
        raise SystemExit(0)
    if info["label"] == os.environ.get("HERDR_MISSING_SESSION_LABEL"):
        add_starting_agent(value, pane, info)
        value.setdefault("_starting", {})[pane] = session
        save(value)
        print("submitted")
        raise SystemExit(0)
    if info["label"] == os.environ.get("HERDR_DELAY_LABEL"):
        add_starting_agent(value, pane, info)
        value.setdefault("_pending", {})[pane] = {
            "remaining": int(os.environ.get("HERDR_DELAY_POLLS", "2")),
            "info": info, "session": session,
        }
        save(value)
        print("submitted")
        raise SystemExit(0)
    if info["label"] == os.environ.get("HERDR_WRONG_SESSION_LABEL"):
        session = str(Path(session).with_name("wrong-session.jsonl"))
    cwd = info["cwd"]
    if info["label"] == os.environ.get("HERDR_WRONG_CWD_LABEL"):
        cwd = str(Path(info["cwd"]).parent)
    add_agent(value, pane, info, session, cwd)
    save(value)
    print("submitted")
    raise SystemExit(0)
if args[:2] == ["tab", "close"]:
    tab = args[2]
    closing = next((info for info in created.values() if info["tab_id"] == tab), None)
    if closing and closing["label"] == os.environ.get("HERDR_REFUSE_CLOSE_LABEL"):
        pane = next(pane for pane, info in created.items() if info["tab_id"] == tab)
        session = value.setdefault("_starting", {}).pop(pane)
        add_agent(value, pane, closing, session)
        save(value)
        print("cannot close root tab", file=sys.stderr)
        raise SystemExit(9)
    value["tabs"] = [t for t in value["tabs"] if t.get("tab_id") != tab]
    value["agents"] = [a for a in value["agents"] if a.get("tab_id") != tab]
    for pane in [p for p, info in created.items() if info["tab_id"] == tab]:
        created.pop(pane)
        value.setdefault("_pending", {}).pop(pane, None)
        value.setdefault("_starting", {}).pop(pane, None)
    save(value)
    print("ok")
    raise SystemExit(0)
if args[:2] == ["tab", "focus"]:
    tab = args[2]
    for item in value["tabs"]: item["focused"] = item.get("tab_id") == tab
    for item in value["agents"]: item["focused"] = item.get("tab_id") == tab
    value["focused_tab_id"] = tab
    save(value)
    print("ok")
    raise SystemExit(0)
print("unsupported herdr command", file=sys.stderr)
raise SystemExit(2)
'''


def checked(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True, check=True)


class PiDeskTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = self.root / "repo"
        checked(["git", "init", "-b", "main", str(self.repo)])
        checked(["git", "-C", str(self.repo), "config", "user.name", "Test"])
        checked(["git", "-C", str(self.repo), "config", "user.email", "test@example.invalid"])
        (self.repo / "shared.txt").write_text("base\n")
        checked(["git", "-C", str(self.repo), "add", "shared.txt"])
        checked(["git", "-C", str(self.repo), "commit", "-m", "base"])
        self.worktrees: list[Path] = []
        for number in (1, 2):
            path = self.root / f"worker {number} tree"
            checked(["git", "-C", str(self.repo), "worktree", "add", "-b", f"work/worker-{number}", str(path)])
            self.worktrees.append(path)

        self.sessions = self.root / "sessions"
        self.sessions.mkdir()
        self.session_paths = [self.sessions / "orchestrator session.jsonl"]
        self.session_paths += [self.sessions / f"worker {number} session.jsonl" for number in (1, 2)]
        self.session_paths += [self.sessions / "unmanaged session.jsonl"]
        for path in self.session_paths:
            path.write_text('{"type":"session"}\n')

        self.worker_state = self.root / "worker-state"
        records = self.worker_state / "workers"
        records.mkdir(parents=True)
        for number, worktree in enumerate(self.worktrees, 1):
            head = checked(["git", "-C", str(worktree), "rev-parse", "HEAD"]).stdout.strip()
            state = {
                "name": f"worker-{number}", "label": f"Worker {number}", "repository": "app",
                "repo_root": str(self.repo), "worktree": str(worktree), "branch": f"work/worker-{number}",
                "base": "origin/main", "workspace_id": "save-workspace", "tab_id": f"save-tab-{number}",
                "pane_id": f"save-pane-{number}", "terminal_id": f"save-term-{number}",
                "prompted": True, "model": None, "test_head": head,
            }
            (records / f"worker-{number}.json").write_text(json.dumps(state))

        self.leases = self.root / "leases.json"
        self.leases.write_text(json.dumps({str(path): f"worker-{number}" for number, path in enumerate(self.worktrees, 1)}))
        self.snapshot_file = self.root / "snapshot.json"
        self.snapshot_file.write_text(json.dumps(self.saved_snapshot()))
        self.log = self.root / "commands.jsonl"
        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        fake = fake_bin / "fake"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        for command in ("herdr", "treehouse"):
            (fake_bin / command).symlink_to(fake)
        self.env = os.environ | {
            "HOME": str(self.home),
            "XDG_STATE_HOME": str(self.root / "xdg-state"),
            "PI_WORKER_STATE_DIR": str(self.worker_state),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "FAKE_LOG": str(self.log),
            "FAKE_LEASES": str(self.leases),
            "HERDR_SNAPSHOT_FILE": str(self.snapshot_file),
            "HERDR_WORKSPACE_ID": "save-workspace",
            "HERDR_TAB_ID": "save-orchestrator",
            "PI_DESK_STARTUP_TIMEOUT_SECONDS": "0.15",
            "PI_DESK_STARTUP_POLL_SECONDS": "0.01",
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def saved_snapshot(self) -> dict:
        tabs = [
            {"workspace_id": "save-workspace", "tab_id": "save-orchestrator", "label": "Main desk", "number": 1, "pane_count": 1, "focused": True, "agent_status": "idle"},
            {"workspace_id": "save-workspace", "tab_id": "save-tab-1", "label": "Worker one", "number": 2, "pane_count": 1, "focused": False, "agent_status": "idle"},
            {"workspace_id": "save-workspace", "tab_id": "save-tab-2", "label": "Worker two", "number": 3, "pane_count": 1, "focused": False, "agent_status": "done"},
            {"workspace_id": "save-workspace", "tab_id": "save-unmanaged", "label": "Scratch review", "number": 4, "pane_count": 1, "focused": False, "agent_status": "idle"},
        ]
        specs = [
            ("save-orchestrator", "save-orchestrator-pane", self.root / "desk root", self.session_paths[0], "idle"),
            ("save-tab-1", "save-pane-1", self.worktrees[0], self.session_paths[1], "idle"),
            ("save-tab-2", "save-pane-2", self.worktrees[1], self.session_paths[2], "done"),
            ("save-unmanaged", "save-unmanaged-pane", self.root, self.session_paths[3], "idle"),
        ]
        (self.root / "desk root").mkdir(exist_ok=True)
        agents = []
        for tab, pane, cwd, session, status_value in specs:
            agents.append({
                "agent": "pi", "agent_status": status_value, "cwd": str(cwd),
                "workspace_id": "save-workspace", "tab_id": tab, "pane_id": pane,
                "terminal_id": f"term-{pane}", "focused": tab == "save-orchestrator",
                "environment": {"API_TOKEN": "SECRET_VALUE"}, "prompt": "private conversation text",
                "agent_session": {"agent": "pi", "kind": "path", "source": "herdr:pi", "value": str(session)},
            })
        return {
            "focused_workspace_id": "save-workspace", "focused_tab_id": "save-orchestrator",
            "workspaces": [{"workspace_id": "save-workspace", "label": "Test desk", "number": 1, "focused": True}],
            "tabs": tabs, "agents": agents,
        }

    def desk(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(DESK), *args], env=env or self.env, text=True, capture_output=True)

    def commands(self) -> list[list[str]]:
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def manifest(self) -> tuple[Path, dict]:
        path = self.root / "xdg-state/minimalist-pi-orchestrator/desks/sofa.json"
        return path, json.loads(path.read_text())

    def save(self, *extra: str) -> dict:
        result = self.desk("save", "sofa", *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def empty_runtime(self) -> dict[str, str]:
        self.snapshot_file.write_text(json.dumps({
            "focused_workspace_id": "bootstrap", "focused_tab_id": "bootstrap-tab",
            "workspaces": [{"workspace_id": "bootstrap", "label": "Bootstrap", "number": 1, "focused": True}],
            "tabs": [{"workspace_id": "bootstrap", "tab_id": "bootstrap-tab", "label": "Shell", "number": 1, "pane_count": 1, "focused": True}],
            "agents": [],
        }))
        env = dict(self.env)
        env.pop("HERDR_WORKSPACE_ID", None)
        env.pop("HERDR_TAB_ID", None)
        return env

    def test_save_idle_desk_order_manifest_safety_and_previous(self) -> None:
        result = self.save()
        path, manifest = self.manifest()
        self.assertEqual([tab["label"] for tab in manifest["tabs"]], ["Main desk", "Worker one", "Worker two"])
        self.assertEqual([tab["role"] for tab in manifest["tabs"]], ["orchestrator", "managed_worker", "managed_worker"])
        self.assertIn("Excluded unmanaged", result["warning"])
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        serialized = path.read_text()
        for forbidden in ("prompt", "conversation", "SECRET_VALUE", "environment", "lock"):
            self.assertNotIn(forbidden, serialized)
        original = path.read_text()
        self.save()
        previous = path.with_name("sofa.previous.json")
        self.assertEqual(previous.read_text(), original)
        self.assertEqual(stat.S_IMODE(previous.stat().st_mode), 0o600)

    def test_explicit_unmanaged_tab_and_labels_with_spaces(self) -> None:
        self.save("--include-tab", "save-unmanaged")
        _, manifest = self.manifest()
        self.assertEqual(manifest["tabs"][-1]["role"], "unmanaged")
        self.assertEqual(manifest["tabs"][-1]["label"], "Scratch review")

    def test_save_refuses_working_missing_and_ambiguous_sessions(self) -> None:
        for mode in ("working", "missing", "ambiguous"):
            with self.subTest(mode=mode):
                snapshot = self.saved_snapshot()
                agent = snapshot["agents"][1]
                if mode == "working":
                    agent["agent_status"] = "working"
                elif mode == "missing":
                    agent.pop("agent_session")
                else:
                    agent["agent_session"]["source"] = "unknown"
                self.snapshot_file.write_text(json.dumps(snapshot))
                result = self.desk("save", "unsafe")
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.root / "xdg-state/minimalist-pi-orchestrator/desks/unsafe.json").exists())

    def test_restore_exact_sessions_order_focus_registry_updates_and_idempotence(self) -> None:
        self.save()
        env = self.empty_runtime()
        result = self.desk("restore", "sofa", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.commands()
        creates = [c for c in commands if c[:3] in (["herdr", "workspace", "create"], ["herdr", "tab", "create"])]
        self.assertEqual(len(creates), 3)
        self.assertTrue(all("--no-focus" in command for command in creates))
        runtime_snapshot = json.loads(self.snapshot_file.read_text())
        restored_workspace = next(
            workspace["workspace_id"]
            for workspace in runtime_snapshot["workspaces"]
            if workspace["label"] == "Test desk"
        )
        restored_tabs = sorted(
            (tab for tab in runtime_snapshot["tabs"] if tab["workspace_id"] == restored_workspace),
            key=lambda tab: tab["number"],
        )
        self.assertEqual([tab["label"] for tab in restored_tabs], ["Main desk", "Worker one", "Worker two"])
        self.assertTrue(all(tab["pane_count"] == 1 for tab in restored_tabs))
        pane_runs = [c for c in commands if c[:3] == ["herdr", "pane", "run"]]
        restored_sessions = [shlex.split(c[-1].removeprefix("exec ")) for c in pane_runs]
        self.assertEqual(restored_sessions[-1], ["pi", "--session", str(self.session_paths[0])])
        self.assertCountEqual(restored_sessions, [["pi", "--session", str(path)] for path in self.session_paths[:3]])
        focus = [c for c in commands if c[:3] == ["herdr", "tab", "focus"]]
        self.assertEqual(len(focus), 1)
        for number in (1, 2):
            state = json.loads((self.worker_state / f"workers/worker-{number}.json").read_text())
            self.assertTrue(state["workspace_id"].startswith("desk-w"))
            self.assertTrue(state["tab_id"].startswith("desk-t"))
            self.assertTrue(state["pane_id"].startswith("desk-p"))
        before = len([c for c in self.commands() if c[:3] == ["herdr", "pane", "run"]])
        again = self.desk("restore", "sofa", env=env)
        self.assertEqual(again.returncode, 0, again.stderr)
        after = len([c for c in self.commands() if c[:3] == ["herdr", "pane", "run"]])
        self.assertEqual(after, before)

    def test_dirty_wip_is_restored_without_modification(self) -> None:
        self.save()
        dirty = self.worktrees[0] / "uncommitted file.txt"
        dirty.write_text("valuable WIP\n")
        result = self.desk("restore", "sofa", env=self.empty_runtime())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(dirty.read_text(), "valuable WIP\n")
        self.assertFalse(any(c[:2] == ["treehouse", "return"] for c in self.commands()))

    def test_restore_refuses_missing_session_worktree_lease_branch_and_conflicts(self) -> None:
        cases = ("session", "worktree", "lease", "branch", "head", "conflict")
        for mode in cases:
            with self.subTest(mode=mode):
                # Rebuild a valid save before each isolated mutation.
                self.snapshot_file.write_text(json.dumps(self.saved_snapshot()))
                self.save()
                path, manifest = self.manifest()
                if mode == "session":
                    Path(manifest["tabs"][0]["session"]).unlink()
                elif mode == "worktree":
                    self.worktrees[0].rename(self.root / "temporarily-missing-worktree")
                elif mode == "lease":
                    leases = json.loads(self.leases.read_text())
                    leases[str(self.worktrees[0])] = "someone-else"
                    self.leases.write_text(json.dumps(leases))
                elif mode == "branch":
                    checked(["git", "-C", str(self.worktrees[0]), "branch", "-m", "work/moved"])
                elif mode == "head":
                    (self.worktrees[0] / "head-moved.txt").write_text("new commit\n")
                    checked(["git", "-C", str(self.worktrees[0]), "add", "head-moved.txt"])
                    checked(["git", "-C", str(self.worktrees[0]), "commit", "-m", "move HEAD"])
                else:
                    other = self.root / "other"
                    checked(["git", "-C", str(self.repo), "switch", "-c", "other-conflict"])
                    (self.repo / "shared.txt").write_text("other\n")
                    checked(["git", "-C", str(self.repo), "commit", "-am", "other"])
                    checked(["git", "-C", str(self.worktrees[0]), "switch", "work/worker-1"])
                    (self.worktrees[0] / "shared.txt").write_text("worker\n")
                    checked(["git", "-C", str(self.worktrees[0]), "commit", "-am", "worker"])
                    # Update saved HEAD to the worker commit, then create a conflict without advancing HEAD.
                    manifest["tabs"][1]["managed"]["head"] = checked(["git", "-C", str(self.worktrees[0]), "rev-parse", "HEAD"]).stdout.strip()
                    path.write_text(json.dumps(manifest))
                    subprocess.run(["git", "-C", str(self.worktrees[0]), "merge", "other-conflict"], text=True, capture_output=True)
                command_count = len(self.commands())
                result = self.desk("restore", "sofa", env=self.empty_runtime())
                self.assertNotEqual(result.returncode, 0)
                new_commands = self.commands()[command_count:]
                self.assertFalse(any(c[:3] == ["herdr", "workspace", "create"] for c in new_commands))
                # Undo mutations needed by later subtests.
                if mode == "session":
                    self.session_paths[0].write_text('{"type":"session"}\n')
                elif mode == "worktree":
                    (self.root / "temporarily-missing-worktree").rename(self.worktrees[0])
                elif mode == "lease":
                    self.leases.write_text(json.dumps({str(p): f"worker-{n}" for n, p in enumerate(self.worktrees, 1)}))
                elif mode == "branch":
                    checked(["git", "-C", str(self.worktrees[0]), "branch", "-m", "work/worker-1"])
                elif mode == "head":
                    checked(["git", "-C", str(self.worktrees[0]), "reset", "--hard", "HEAD^"])
                elif mode == "conflict":
                    checked(["git", "-C", str(self.worktrees[0]), "merge", "--abort"])

    def test_submitted_command_with_no_pi_times_out_without_registry_update_and_retries(self) -> None:
        self.save()
        registry = self.worker_state / "workers/worker-1.json"
        original_registry = registry.read_text()
        env = self.empty_runtime() | {"HERDR_NEVER_LABEL": "Worker one"}
        partial = self.desk("restore", "sofa", env=env)
        self.assertEqual(partial.returncode, 1)
        self.assertIn("timed out", partial.stderr)
        self.assertEqual(registry.read_text(), original_registry)
        self.assertFalse(any(c[:2] == ["treehouse", "return"] for c in self.commands()))
        closed = [c for c in self.commands() if c[:3] == ["herdr", "tab", "close"]]
        self.assertEqual(len(closed), 1)

        retry_env = dict(env)
        retry_env.pop("HERDR_NEVER_LABEL")
        retry = self.desk("restore", "sofa", env=retry_env)
        self.assertEqual(retry.returncode, 0, retry.stderr)
        updated = json.loads(registry.read_text())
        self.assertNotEqual(updated["tab_id"], "save-tab-1")
        runs_after_retry = len([c for c in self.commands() if c[:3] == ["herdr", "pane", "run"]])
        again = self.desk("restore", "sofa", env=retry_env)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(
            len([c for c in self.commands() if c[:3] == ["herdr", "pane", "run"]]),
            runs_after_retry,
        )

    def test_pi_without_session_identity_times_out_without_registry_update(self) -> None:
        self.save()
        registry = self.worker_state / "workers/worker-1.json"
        original_registry = registry.read_text()
        env = self.empty_runtime() | {"HERDR_MISSING_SESSION_LABEL": "Worker one"}
        result = self.desk("restore", "sofa", env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("timed out", result.stderr)
        self.assertIn("session identity has not appeared", result.stderr)
        self.assertEqual(registry.read_text(), original_registry)
        self.assertEqual(
            len([c for c in self.commands() if c[:3] == ["herdr", "tab", "close"]]),
            1,
        )

    def test_submitted_command_with_wrong_session_leaves_registry_unchanged(self) -> None:
        self.save()
        registry = self.worker_state / "workers/worker-1.json"
        original_registry = registry.read_text()
        env = self.empty_runtime() | {"HERDR_WRONG_SESSION_LABEL": "Worker one"}
        result = self.desk("restore", "sofa", env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("session mismatch", result.stderr)
        self.assertEqual(registry.read_text(), original_registry)
        self.assertFalse(any(c[:2] == ["treehouse", "return"] for c in self.commands()))

    def test_submitted_command_with_wrong_cwd_leaves_registry_unchanged(self) -> None:
        self.save()
        registry = self.worker_state / "workers/worker-1.json"
        original_registry = registry.read_text()
        env = self.empty_runtime() | {"HERDR_WRONG_CWD_LABEL": "Worker one"}
        result = self.desk("restore", "sofa", env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("cwd mismatch", result.stderr)
        self.assertEqual(registry.read_text(), original_registry)
        self.assertFalse(any(c[:2] == ["treehouse", "return"] for c in self.commands()))

    def test_pi_appears_without_identity_then_exact_session_completes_handshake(self) -> None:
        self.save()
        registry = self.worker_state / "workers/worker-1.json"
        env = self.empty_runtime() | {
            "HERDR_DELAY_LABEL": "Worker one",
            "HERDR_DELAY_POLLS": "3",
        }
        result = self.desk("restore", "sofa", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(registry.read_text())
        self.assertNotEqual(state["tab_id"], "save-tab-1")
        self.assertFalse(any(c[:3] == ["herdr", "tab", "close"] for c in self.commands()))
        snapshots = [c for c in self.commands() if c[:3] == ["herdr", "api", "snapshot"]]
        self.assertGreaterEqual(len(snapshots), 5)

    def test_root_close_failure_with_late_orchestrator_is_deduplicated_on_retry(self) -> None:
        self.save()
        env = self.empty_runtime() | {
            "HERDR_FAIL_LABELS": "Worker one,Worker two",
            "HERDR_MISSING_SESSION_LABEL": "Main desk",
            "HERDR_REFUSE_CLOSE_LABEL": "Main desk",
        }
        partial = self.desk("restore", "sofa", env=env)
        self.assertEqual(partial.returncode, 1)
        self.assertEqual(json.loads(partial.stderr)["tabs_available"], 0)

        retry_env = dict(env)
        for key in ("HERDR_FAIL_LABELS", "HERDR_MISSING_SESSION_LABEL", "HERDR_REFUSE_CLOSE_LABEL"):
            retry_env.pop(key)
        retry = self.desk("restore", "sofa", env=retry_env)
        self.assertEqual(retry.returncode, 0, retry.stderr)
        runs = [shlex.split(c[-1])[-1] for c in self.commands() if c[:3] == ["herdr", "pane", "run"]]
        self.assertEqual(runs.count(str(self.session_paths[0])), 1)
        self.assertEqual(runs.count(str(self.session_paths[1])), 2)
        self.assertEqual(runs.count(str(self.session_paths[2])), 2)
        worker_one = json.loads((self.worker_state / "workers/worker-1.json").read_text())
        self.assertNotEqual(worker_one["tab_id"], "save-tab-1")

    def test_partial_start_failure_preserves_wip_and_is_retryable(self) -> None:
        self.save()
        dirty = self.worktrees[1] / "keep me.txt"
        dirty.write_text("WIP\n")
        env = self.empty_runtime() | {"HERDR_FAIL_LABEL": "Worker two"}
        partial = self.desk("restore", "sofa", env=env)
        self.assertEqual(partial.returncode, 1)
        self.assertIn("partial", partial.stderr.lower())
        self.assertEqual(dirty.read_text(), "WIP\n")
        self.assertFalse(any(c[:2] == ["treehouse", "return"] for c in self.commands()))
        worker_two = json.loads((self.worker_state / "workers/worker-2.json").read_text())
        self.assertEqual(worker_two["tab_id"], "save-tab-2")
        retry_env = dict(env)
        retry_env.pop("HERDR_FAIL_LABEL")
        retry = self.desk("restore", "sofa", env=retry_env)
        self.assertEqual(retry.returncode, 0, retry.stderr)
        runs = [c for c in self.commands() if c[:3] == ["herdr", "pane", "run"]]
        sessions = [shlex.split(c[-1])[-1] for c in runs]
        self.assertEqual(sessions.count(str(self.session_paths[1])), 1)
        self.assertEqual(sessions.count(str(self.session_paths[2])), 2)  # failed attempt plus successful retry


if __name__ == "__main__":
    unittest.main()
