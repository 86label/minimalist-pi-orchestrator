# Architecture

Minimalist Pi Orchestrator has three components:

- `pi-worker` owns repository validation, Treehouse lease acquisition, Git branch creation, Herdr tab startup, lifecycle records, and guarded return.
- `pi-desk` conservatively saves and restores exact Pi sessions that already have durable working directories and leases.
- `src/pi-workers.ts` only translates typed Pi tool calls into `pi-worker` argument vectors and returns its JSON output.

## Worker startup

`pi-worker start` resolves a repository through the explicit allowlist, verifies minimum dependency versions, fetches the configured remote branch, acquires a durable Treehouse lease, and validates that the returned linked worktree is exactly at the fetched commit. It then creates a unique `work/<name>` branch and a dedicated one-pane Herdr tab before starting Pi.

Lifecycle mutation is serialized with a filesystem lock. State writes are atomic and owner-only. If startup fails, rollback closes only the tab created by that attempt, force-returns only its new lease, and removes only its unneeded startup branch.

## Desk recovery

`pi-desk save` joins Herdr's Pi session snapshot to worker records and Treehouse lease status. It writes only the identities needed to validate a later restore.

`pi-desk restore` validates all durable identities before creating UI. After submitting each exact `pi --session` command, it waits for Herdr to report the expected pane, session path, working directory, runtime identity, and a usable Pi status. Only a complete handshake updates transient Herdr IDs in a worker record.

Recovery never owns source work or leases. It does not commit, clean, reset, switch, repair, allocate, or return a worktree.

## State ownership

- Git owns commits and branches.
- Treehouse owns worktree pools and durable leases.
- Herdr owns workspaces, tabs, panes, and terminal processes.
- Pi owns coding conversations and session files.
- Minimalist Pi Orchestrator stores only the small identity records connecting those systems.

State defaults to `${XDG_STATE_HOME:-~/.local/state}/minimalist-pi-orchestrator/` with owner-only permissions.

## Intentional non-features

The integration does not inspect a task catalog, claim work, dispatch automatically, assign roles, implement stages, retry tasks, enforce budgets, or maintain workflow state. A human directs every session.
