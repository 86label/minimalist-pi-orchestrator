# Minimalist Pi Orchestrator

A small, human-directed bridge between [Pi](https://github.com/earendil-works/pi), [Herdr](https://github.com/86label/herdr), and [Treehouse](https://github.com/kunchenguid/treehouse).

It opens visible Pi sessions in dedicated Herdr tabs, with one isolated Treehouse worktree and Git branch per session. It can also save and restore an idle desk across host restarts.

This is intentionally **not** a workflow engine. It has no queues, automatic dispatch, task claiming, roles, stages, retries, budgets, or workflow database. A human decides when to create, direct, review, and return each session.

## Platform and prerequisites

Minimalist Pi Orchestrator supports **Linux only**.

Minimum versions:

- Python 3.10
- Git 2.31
- Node.js 22.19
- [Pi `@earendil-works/pi-coding-agent`](https://www.npmjs.com/package/@earendil-works/pi-coding-agent) 0.80.10
- [Herdr](https://github.com/86label/herdr) 0.7.4
- [Treehouse](https://github.com/kunchenguid/treehouse) 2.0.0

All five commands—`python3`, `git`, `pi`, `herdr`, and `treehouse`—must be on `PATH`. Install and configure the upstream tools before installing this project.

## Install

Clone a tagged release into a stable directory, verify it, and install copies:

```bash
git clone --branch v0.1.0 https://github.com/86label/minimalist-pi-orchestrator.git
cd minimalist-pi-orchestrator
npm ci
npm run check
python3 -m unittest discover -s tests -v
./install.sh
```

The installer copies:

- `pi-worker` and `pi-desk` to `~/.local/bin`;
- the extension to `~/.pi/agent/extensions/minimalist-pi-orchestrator.ts`;
- a repository configuration example to `${XDG_CONFIG_HOME:-~/.config}/pi-worker/`.

It never overwrites repository configuration. Existing different installed files are refused unless `--backup` is explicit.

`./install.sh --link` is available for development from a stable checkout. Do not link from a disposable worktree.

Restart Pi or run `/reload` after installation.

## Register repositories

Edit `${XDG_CONFIG_HOME:-~/.config}/pi-worker/repos.json`:

```json
{
  "default_repository": "example-app",
  "repositories": {
    "example-app": {
      "path": "~/projects/example-app",
      "remote": "origin",
      "default_branch": "main"
    }
  }
}
```

This is an explicit allowlist, not discovery. Each path must be the primary checkout of a Git repository configured for Treehouse. Startup fetches the configured remote branch and refuses stale or mismatched worktrees.

## Use

Run Pi inside a Herdr workspace and ask naturally:

- “Open a tab for me to work on the parser.”
- “Delegate the agreed documentation update.”

The extension provides typed tools to:

- spawn a visible worker in an isolated lease and branch;
- list workers with conservative Herdr/Pi, Git, lease, and pull-request evidence;
- inspect one exact worker with bounded recent pane output;
- send one short follow-up, focus its tab, or resume a reconciled exact session;
- restore all missing managed workers without a prior desk save;
- close a worker and return its lease while retaining its Pi transcript.

A human-led session is normally empty and focused. A delegated session receives a self-contained prompt and normally opens without stealing focus. Managed workers do not receive orchestration tools and cannot start nested workers; ask the orchestrator to create siblings instead.

Returning a dirty worktree is refused. Destructive return requires interactive human confirmation. The Git branch survives a normal return.

### Project trust

Workers start Pi with `--approve`. This trusts project-local Pi settings, extensions, skills, and other executable project resources for that run. Register and open only repositories whose contents you trust. Treehouse worktrees isolate Git working state; they are not a security sandbox or credential boundary.

## Restore managed workers

Each new worker receives a unique Pi session ID and private session directory under the orchestrator state root. Its registry record therefore contains enough durable identity to recreate a missing tab without an explicit desk save:

```bash
pi-worker restore-all
```

The typed `restore_pi_workers` tool exposes the same operation. Restore preflights every recorded session file, linked worktree, branch, and Treehouse lease before creating tabs. Exact workers already live are left alone, ambiguity stops safely, and successful handshakes update transient Herdr IDs.

## Optional full-desk save and restore

A desk manifest is only needed to preserve the orchestrator conversation, unmanaged Pi tabs, workspace label, ordering, and focus. When every included Pi is idle or done, save from the orchestrator Pi tab:

```bash
pi-desk save my-desk
```

Read any warning about excluded unmanaged Pi tabs, then exit each Pi normally before shutdown so its session is flushed.

After restart, run this from an ordinary Herdr shell, not from a Pi tool call:

```bash
pi-desk restore my-desk
```

Restore validates exact Pi session files, working directories, managed Git branches and commits, worker records, and Treehouse lease holders before creating UI. It resumes the orchestrator last and focuses it. A partial restore is safe to retry after correcting the reported discrepancy.

Desk recovery never commits, cleans, resets, switches, reallocates, or returns worktrees. Dirty work is preserved. It cannot recover conversation data that Pi did not flush before an unexpected host failure.

State is stored with owner-only permissions under:

```text
${XDG_STATE_HOME:-~/.local/state}/minimalist-pi-orchestrator/
```

Worker records and desk manifests contain local repository, worktree, branch, and session paths but no conversation text. The private `sessions/` directory contains Pi JSONL transcripts, which may include prompts, model responses, source excerpts, tool output, and any sensitive text entered during a session. Normal worker return retains these transcripts; remove them only through an explicit retention policy or deliberate manual cleanup.

## Workspace template

For a dedicated orchestration directory, use the guarded non-overwriting procedure in [Human-directed orchestration](docs/orchestration.md#installing-the-workspace-template). Review and adapt the files without adding autonomous behavior.

## Documentation

- [Architecture](docs/architecture.md)
- [Installation](docs/installation.md)
- [Repository registration](docs/repository-registration.md)
- [Worker lifecycle](docs/lifecycle.md)
- [Human-directed orchestration](docs/orchestration.md)
- [Desk suspend/resume](docs/desk-suspend-resume.md)
- [Recovery](docs/recovery.md)
- [Troubleshooting](docs/troubleshooting.md)

## Diagnostics and privacy

```bash
pi-worker status
herdr status
treehouse status
```

These commands and error messages may contain usernames, repository paths, branch names, tab labels, session paths, or remote errors. Redact diagnostic output before sharing it publicly.

## Development

```bash
npm ci
npm run check
npm test
python3 -m py_compile bin/pi-worker bin/pi-desk
python3 -m unittest discover -s tests -v
bash -n install.sh
```

Tests use temporary Git repositories and fake Pi, Herdr, and Treehouse executables. They do not allocate real leases or tabs.

## Support and contributions

This is unsupported personal software, provided as-is. No support, security response, compatibility assistance, issues, or feature requests are offered. Contributions are not accepted. The source and documentation are available as implementation information for users who choose to evaluate it themselves.

## Attribution

Minimalist Pi Orchestrator integrates with, but is not affiliated with:

- [Pi](https://github.com/earendil-works/pi), MIT licensed, authored by Mario Zechner and its maintainers;
- [Herdr](https://github.com/86label/herdr), AGPL-3.0-or-later or commercially licensed;
- [Treehouse](https://github.com/kunchenguid/treehouse), MIT licensed.

Their names and licenses apply to their respective projects. This repository does not redistribute their binaries.

## License

[MIT](LICENSE) © 2026 Lasse Abelsen.
