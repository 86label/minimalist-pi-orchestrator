# Recovery

Startup is transactional within the available command boundaries. If anything fails after lease acquisition, the launcher closes only the tab it created, force-returns that new lease, and removes the startup branch. It does not close the caller's tab.

If a process or host dies before rollback completes:

1. Run `pi-worker status`, then `pi-worker inspect NAME` for bounded native state, pane output, Git/lease/PR evidence. A missing process is not authority to return a lease.
2. Run `pi-worker restore-all` to recreate every missing managed worker whose deterministic session file, linked worktree, branch, and lease still match. No desk manifest is required.
3. When only one recorded tab remains without Pi, `pi-worker resume NAME` can submit its exact session in that recorded pane. It does not allocate or repair anything.
4. Missing session files and ambiguous identities require human reconciliation. Use `pi-desk restore` only when recovering a previously saved complete desk.
5. Preserve or commit valuable changes in the worktree before return. Use `--force` only when deliberately discarding dirty files.
6. If no record exists, inspect Treehouse's leases and Git's `worktree list` before manually returning anything. Do not guess at paths or holders.

A state record is intentionally minimal and may be inspected as JSON under `${XDG_STATE_HOME:-~/.local/state}/minimalist-pi-orchestrator/workers/`. Do not edit it while a launcher command is running. If Herdr is unavailable during return, pane/tab closure is best-effort but Treehouse return remains authoritative and must succeed before metadata is deleted.

Branches and Pi transcripts survive normal return. Recover source work from the recorded branch rather than from a removed worktree path. Retained transcripts under the private `sessions/` state subtree may contain full conversation and tool content; delete them only deliberately.

## Desk restore recovery

A desk manifest is diagnostic state, not authority to repair WIP. `pi-desk restore` retains it after success or failure and is safe to retry after correcting a reported discrepancy. A missing tab with a valid exact session, registry record, linked worktree, branch/HEAD, and lease holder can be recreated. A missing session, moved worktree, changed ownership, branch/HEAD mismatch, or unresolved conflict stops before Herdr mutation.

On partial Pi startup, only sessions that completed the exact pane/session/cwd/status handshake are counted as available and receive managed runtime IDs. Herdr can report `agent: pi` before the Pi integration publishes session identity; restore keeps polling this and other incomplete startup metadata until the bounded deadline. A complete wrong identity still fails closed immediately. A command-submission success without a matching Pi by the deadline is a failure: restore attempts to close its newly created tab and leaves registry IDs unchanged. Closure is best-effort, so a root tab that Herdr cannot close—or a session published just after timeout—can remain live. No worktree or lease is touched. Fix the executable/session/Herdr issue and rerun restore; exact live sessions are deduplicated while missing workers are restored and reconciled to their new runtime IDs. Never allocate a replacement worktree, delete a manifest or lock, or clean/reset WIP to make reconciliation pass.
