# Architecture

Minimalist Pi Orchestrator has three deliberately small components:

- `bin/pi-worker` owns deterministic repository validation, Treehouse leases, Git branches, Herdr tabs, exact-worker controls, lifecycle records, rollback, and guarded return.
- `bin/pi-desk` conservatively saves and restores exact Pi sessions that already have durable working directories and leases.
- `src/pi-workers.ts` is a thin typed adapter from Pi tools to `pi-worker` arguments and JSON results.

## Sources of truth

Git owns branches and commits, Treehouse owns worktree pools and leases, Herdr owns workspaces/tabs/panes and live Pi telemetry, and Pi owns conversations and session files. The orchestrator stores only the small identity records connecting those systems.

A workspace `AGENTS.md` can route the orchestrator to a human-owned `ORCHESTRATION.md`. Operating policy belongs there rather than in launcher mechanics or tool descriptions.

Managed worker processes inherit `PI_WORKER_NAME`. The extension registers no orchestration tools in those processes, and `pi-worker start` refuses nested starts. This prevents accidental nesting but is not a security boundary; a human can create sibling workers from the orchestrator.

## Worker lifecycle

Startup resolves only an allowlisted repository, verifies minimum dependency versions, fetches the configured remote/default branch, obtains a Treehouse lease, and validates that the result is an absolute linked-worktree root exactly at the fetched commit. It then creates a unique branch, unique Pi session ID, owner-only session directory, and dedicated Herdr tab before starting Pi with deterministic session storage.

Lifecycle mutation is serialized with an owner-only filesystem lock. Records are written atomically with owner-only permissions. Startup rollback closes only the tab created by that attempt, force-returns only a confirmed linked worktree, and removes only its unneeded startup branch.

Status and inspection join registry identity with bounded Herdr/Pi, Git, Treehouse lease, and GitHub pull-request evidence. Exact follow-up, focus, and resume operations revalidate recorded runtime identity immediately before mutation and stop on missing or ambiguous identity. Follow-up submits Enter once and never retries it. Resume never allocates replacement resources.

Managed-worker restore is registry-driven and needs no desk manifest. It preflights exact session files, linked worktrees, branches, and leases before recreating missing tabs, then requires an exact Pi session/cwd/runtime handshake before updating transient Herdr IDs. It never allocates a replacement worktree.

Return refuses dirty work by default and reports conservative Git/PR diagnostics. Destructive return is available only after explicit interactive human confirmation through the Pi extension. The named Git branch and private Pi transcript survive return; the active registry record and Treehouse lease do not.

## Desk recovery

Save joins Herdr's exact Pi session snapshot to worker records and Treehouse lease status. Restore validates every durable identity before creating UI, then waits for the expected pane/session/cwd/status handshake before updating transient runtime IDs.

Recovery never owns source work or leases. It does not commit, clean, reset, switch, repair, allocate, or return a worktree.

State defaults to `${XDG_STATE_HOME:-~/.local/state}/minimalist-pi-orchestrator/`. Worker records and desk manifests contain identity metadata. The owner-only `sessions/` subtree contains full Pi transcripts and is deliberately retained after normal return.

## Intentional non-features

The integration creates visible sessions selected by a human. It does not inspect a catalog and dispatch work, assign roles, implement workflow stages, retry tasks, enforce budgets, or maintain a workflow database.
