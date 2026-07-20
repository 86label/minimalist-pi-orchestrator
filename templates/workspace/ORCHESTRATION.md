# Orchestrator operating model

A Pi session in this directory acts as the conversational orchestrator. Worker Pi sessions run in dedicated Herdr tabs and isolated Treehouse worktrees. These are operating conventions, not workflow automation.

## Start or resume

1. Read `AGENTS.md` and this file.
2. Call `list_pi_workers` to recover recorded worktrees, branches, and Git status.
3. Inspect Herdr only when needed to reconcile records with visible sessions.
4. Ask the human what to resume when intent is unclear.

Git preserves branches, Treehouse preserves leases, Herdr preserves the live terminal desk, and Pi preserves conversations. Conversation context alone is not authoritative lifecycle state.

## Create sessions

Interpret ordinary requests conversationally:

- “Open a tab for me” normally means an empty focused session with no prompt.
- “Delegate this” normally means a non-focused session with a self-contained prompt.
- After a discussion, summarize the agreed objective, constraints, acceptance criteria, and relevant references without inventing requirements.

Use `spawn_pi_worker`, not ad hoc setup. Every worker receives its own Herdr tab. Omit the repository to use the configured default unless another registered repository is clearly identified.

## Observe and return

Use `list_pi_workers` for durable status. Inspect a worker when the human asks or coordination requires it; do not poll continuously. Idle status alone is not proof of success, so inspect its output and branch before treating work as complete.

After work is integrated or deliberately abandoned, use `return_pi_worker`. A dirty worktree must be preserved unless the human explicitly requests destructive force return. Normal return leaves the Git branch available.

## Save and restore

When included Pi sessions are idle, run `pi-desk save NAME` from the orchestrator and then exit each Pi normally before shutdown. Leave worker leases allocated.

After restart, run `pi-desk restore NAME` from an ordinary Herdr shell. If validation fails, preserve the worktree and reconcile the reported identity mismatch. Never clean, reset, switch, reallocate, or force-return work merely to make restore pass.

## Boundaries

Keep orchestration small and human-directed. Do not add queues, automatic dispatch, autonomous task claiming, role pipelines, mandatory stages, retries, token budgets, or a workflow database.
