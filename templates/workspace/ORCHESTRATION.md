# Orchestrator operating model

This workspace is a human-directed development desk. A Pi session at this root acts as the conversational orchestrator; visible worker Pi sessions run in independent Herdr tabs and isolated Treehouse worktrees. The human decides what to discuss, create, direct, review, merge, stop, or abandon.

## Start or resume

1. Read `AGENTS.md` and this file.
2. Call `list_pi_workers` to recover recorded identities and conservative status.
3. Use `inspect_pi_worker` only when needed to reconcile a worker or understand progress.
4. Ask the human what to resume when intent is unclear.

Git owns commits and branches, Treehouse owns leases, Herdr owns the live desk, Pi owns conversations, and the worker registry connects them. Conversation context is not authoritative lifecycle state.

Managed workers carry `PI_WORKER_NAME`, receive no orchestration tools, and cannot call `pi-worker start`. Ask the orchestrator to create sibling workers when the human wants decomposition.

## Create sessions

Interpret ordinary requests conversationally:

- “Open a tab for me” normally means an empty focused session with no prompt.
- “Delegate this” normally means a non-focused session with a self-contained prompt.
- Summarize agreed objectives, decisions, constraints, acceptance criteria, and open questions without inventing requirements.

Use `spawn_pi_worker`, not ad hoc setup. Omit the repository when the configured default applies. Every worker receives its own tab.

## Observe and communicate

Prefer typed worker tools:

- `list_pi_workers` for bounded recorded status;
- `inspect_pi_worker` for exact identity, recent output, and durable evidence;
- `send_pi_worker_follow_up` for one short follow-up submitted once;
- `focus_pi_worker` when the human wants to take over;
- `resume_pi_worker` only for a reconciled exact session in its recorded pane;
- `restore_pi_workers` to recreate all missing managed workers without a desk save.

Do not poll continuously. Idle status does not prove completion. Missing or ambiguous identity must stop mutation and trigger conservative reconciliation.

## Restore and return

Managed workers have deterministic private Pi sessions. After restart, use `restore_pi_workers` to recreate missing managed tabs directly from durable records. No prior save is required.

Use `pi-desk save NAME` only to preserve the complete desk: orchestrator conversation, unmanaged tabs, workspace label, order, and focus. Exit Pi normally after saving so sessions flush, then run `pi-desk restore NAME` from an ordinary Herdr shell. Never clean, reset, switch, reallocate, or force-return work merely to make either restore path pass.

After work is integrated or deliberately abandoned, use `return_pi_worker`. Preserve dirty worktrees. `force=true` requires explicit interactive human confirmation to discard uncommitted changes. Normal return removes the active record and lease while retaining the branch and private Pi transcript. Transcript deletion is a separate explicit decision.

## Recovery

Reconcile registry, Herdr, Treehouse, and Git conservatively:

- inspect a recorded worktree and branch when its tab is missing;
- inspect cwd, branch, and lease holder when a visible tab lacks a record;
- preserve an exited worker's durable lease until the human chooses resume or return;
- preserve dirty or conflicted work;
- close only the pane for a legacy worker sharing the orchestrator tab;
- never delete locks, holder metadata, branches, or worktrees merely because they appear stale.

## Boundaries

The integration may create, inspect, message, focus, resume, and safely return visible workers. It must not grow autonomous task consumption, task queues, automatic dispatch, role pipelines, mandatory stages, retries, budgets, or a workflow database.
