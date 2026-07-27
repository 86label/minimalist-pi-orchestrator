# Optional full-desk suspend and resume

Managed workers can be recreated without a desk manifest using `pi-worker restore-all`. Use `pi-desk` only when the complete semantic desk must also be preserved across a host restart: Pi session identities, tab order and labels, and references to existing durably leased worker worktrees. It does not preserve processes or Herdr runtime IDs, and it never commits, cleans, switches, resets, returns, or reallocates a worker.

## End-of-day checklist

From the orchestrator Pi tab:

1. Let every Pi included in the desk reach `idle` or `done`. Saving fails closed for working, blocked, ambiguous, or session-less tabs.
2. Run `pi-desk save NAME`.
3. Read any warning about excluded unmanaged Pi tabs. Include one deliberately by Herdr tab ID when needed:

   ```bash
   pi-desk save NAME --include-tab TAB_ID
   ```

4. Confirm the command reports the expected tab count and manifest path.
5. Exit each Pi normally so its JSONL session is flushed before shutting down the host.

Save includes the current orchestrator and managed workers in their Herdr tab order. Other Pi tabs are excluded unless explicitly named. It validates Pi session files, linked managed worktrees, branches, HEAD commits, registry identity, and Treehouse lease holders. It does **not** close the currently executing orchestrator, close any other tab, or return a lease.

## Next-morning checklist

From an ordinary Herdr shell—not from a Pi tool call—run:

```bash
pi-desk restore NAME
```

Restore preflights the entire manifest before changing Herdr. When no saved session is already live, it creates a workspace with the saved label, creates dedicated one-pane tabs in saved order, then launches each as:

```bash
pi --session EXACT_RECORDED_SESSION_PATH
```

The orchestrator is launched last and focused after the restore command has finished its work. After each pane command is submitted, restore waits up to 15 seconds for that exact pane to report Pi, the exact `herdr:pi` session path, expected cwd, and a usable status. Pi may appear in Herdr before its session identity, cwd, runtime identity, or startup status is complete; these transitional snapshots are polled until the same bounded deadline, and a timeout reports the last observed condition. Once Herdr publishes a complete session identity, any mismatch fails closed immediately. Only a completed handshake makes the tab available and permits managed workspace/tab/pane/terminal IDs to replace old registry IDs. Existing dirty WIP is allowed and left byte-for-byte unchanged; unresolved conflicts are preserved but require human resolution before restore.

Run `pi-desk restore NAME` again after fixing a reported partial failure. Sessions already live in Herdr are deduplicated by exact session identity, successful tabs are not restarted, and managed registry runtime IDs are reconciled. The manifest remains available for diagnosis and later retries.

## Manifest and privacy

Version 1 manifests are stored at:

```text
${XDG_STATE_HOME:-~/.local/state}/minimalist-pi-orchestrator/desks/NAME.json
```

`PI_DESK_STATE_DIR` can override the orchestrator state root for testing. Files and directories use restrictive permissions, writes are atomic, and the prior successful save is retained as `NAME.previous.json`.

The manifest contains only save time, workspace label, ordered tab role/label/cwd/session identity/focus, and managed worker identity (name, repository, worktree, branch, HEAD, lease holder, and registry filename). It never copies prompts, conversation text, environment variables, credentials, lock metadata, task documents, source files, or session contents. Separately, the state root's owner-only `sessions/` subtree contains full managed-worker Pi transcripts and is retained after normal worker return.

## Fail-closed rules

Restore refuses to guess or repair when a session/cwd/worktree is missing, a worktree is no longer linked, registry identity differs, branch or HEAD moved, lease ownership changed, conflicts remain, or the same session is live ambiguously. It reports the discrepancy without cleaning, switching, resetting, deleting, force-returning, or allocating a replacement worktree.

A pane submission failure, definitive startup-handshake mismatch, or startup timeout produces a partial nonzero result. Tabs whose Pi handshake succeeded and all durable WIP remain in place; only the newly created failed tab is closed, and its managed registry record retains the prior IDs. Tab closure is best-effort: Herdr may refuse to close the workspace's root tab, and a Pi whose identity arrives after the timeout may therefore remain live. Correct the startup issue and retry; an exact already-live session is deduplicated and missing managed workers are restored with fresh runtime IDs.

For automated tests, `PI_DESK_STARTUP_TIMEOUT_SECONDS` and `PI_DESK_STARTUP_POLL_SECONDS` can shorten the bounded handshake. Both must be positive numeric seconds; normal installations should keep the conservative defaults.
