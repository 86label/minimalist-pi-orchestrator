# Worker lifecycle

## Start

1. Resolve the requested or default repository through the allowlist.
2. Verify dependencies and fetch the configured remote/default branch; stop on failure.
3. Acquire a Treehouse lease using the slugged worker name as durable holder.
4. Reject a primary checkout, non-root path, or worktree not exactly at the fetched commit.
5. Create a unique `work/<name>` branch (`-2`, `-3`, and so on when needed).
6. Explicitly run `herdr tab create`, then `herdr pane run` in its returned root pane. The old `herdr agent start --workspace` approach is intentionally forbidden because it creates a right-hand sibling pane in the caller's tab.
7. Create a unique Pi session ID and owner-only session directory, then start Pi with `--session-dir` and `--session-id`.
8. Atomically record minimal lifecycle metadata, including the deterministic session identity.

An empty human-led session has no prompt and is normally focused. A delegated session has a self-contained prompt and normally does not steal focus. Model selection is optional. Pi arguments are shell-quoted as a single pane command.

## Inspect

`pi-worker status` conservatively reports every record with registry identity, native Herdr/Pi liveness where available, Git status/ahead evidence, Treehouse lease evidence, and reliable PR evidence. `pi-worker inspect NAME` additionally returns at most 80 recent pane lines / 8KB. Classifications are `working`, `blocked`, `idle`, `exited/missing`, or `ambiguous`; labels never authorize a mutation. The Pi extension exposes these as `list_pi_workers` and `inspect_pi_worker`.

## Follow-up, focus, and exact resume

`pi-worker follow-up NAME TEXT` revalidates the full recorded Pi workspace/tab/pane/(when present terminal) identity, types text once, and sends one Enter. It never retries Enter. Enter rejection is an error after typing; accepted Enter is still reported as submission-inconclusive because pane output cannot prove Pi consumed it. `pi-worker focus NAME` focuses the exact recorded tab. `pi-worker resume NAME` only submits `pi --session` in the recorded pane when a previously reconciled exact Pi session path exists, the pane is missing Pi but its tab remains exact, and the recorded worktree still exists. It never allocates a replacement lease/worktree. Use `pi-desk restore` when the tab is missing or identity is ambiguous.

There is intentionally no continuous worker polling or background notification service. Herdr/Pi native state is inspected on request; this avoids notification loops and autonomous control machinery.

## Managed-worker restore

`pi-worker restore-all` recreates missing managed workers directly from their durable registry records; no desk save is required. Before any Herdr mutation it validates every exact session file, linked worktree root, current branch, and Treehouse lease holder. Existing exact live workers are left alone. Missing tabs are recreated in the caller's workspace, and registry runtime IDs change only after the resumed Pi reports the exact session path, cwd, and Herdr identity with a usable status. Partial runtime failures retain all work and are safe to retry.

## Optional full-desk suspend and resume

`pi-desk save NAME` remains useful when the human wants to preserve the orchestrator conversation, unmanaged Pi tabs, workspace label, tab order, and focus. It records an idle desk without closing Pi, returning leases, or changing worktrees. `pi-desk restore NAME` recreates that complete semantic desk. See [Desk suspend/resume](desk-suspend-resume.md).

## Return

`pi-worker return NAME` refuses a dirty worktree. `--force` is destructive and must be explicitly requested. Its report distinguishes dirty work, commits relative to the recorded base with no upstream (local-only/unpublished warning), upstream-ahead work, known PR state when `gh` can establish it, merged-into-base evidence, and unavailable/ambiguous PR evidence. Dedicated worker tabs are closed; legacy/shared tabs close only the recorded pane and never the caller's orchestrator tab. Treehouse then returns the worktree and the active metadata record is removed. The Git branch remains available for review, push, or integration, and the private Pi transcript remains under the state root. Transcript deletion is a separate explicit retention decision, never part of normal return.
