# Troubleshooting

## Repository config not found or unknown repository

Create `~/.config/pi-worker/repos.json` from `config/repos.example.json` and register the repository by name. Check `$PI_WORKER_CONFIG` and `$XDG_CONFIG_HOME` if using alternate roots.

## Fetch failed

Verify network access, remote name, default branch, and Git credentials manually. The launcher intentionally does not fall back to a stale ref.

## Invalid or primary worktree

Treehouse must return an absolute linked-worktree root at the freshly fetched commit. Check Treehouse configuration and leases; the launcher will never operate in the primary checkout.

## No focused Herdr workspace

Run from inside Herdr or pass `--workspace`. `HERDR_WORKSPACE_ID` is preferred when available.

## Dirty worker cannot be returned

Review `git status` in the reported worktree, then commit or otherwise preserve changes. Pass `--force` only to knowingly discard them.

## Managed worker restore is refused

`pi-worker restore-all` requires a unique exact session file, absolute linked worktree root, expected current branch, and exact Treehouse lease holder for every record before creating tabs. Correct the reported identity mismatch conservatively. Never manufacture a session, reset a branch, move a worktree, or alter lease metadata merely to pass preflight.

A partial runtime failure can leave successfully handshaken workers live while failed new tabs are closed best-effort. Correct the Herdr/Pi startup issue and retry; exact live workers are left alone.

## Desk save says a Pi is not idle

Wait for the Pi tool/turn to finish and save again. A blocked, working, ambiguous, or session-less Pi is intentionally not captured. There is no unsafe override. Unmanaged Pi tabs require an explicit repeatable `--include-tab TAB_ID`.

## Desk restore reports an identity mismatch

Treat the message as a reconciliation problem, not permission to repair automatically. Compare the manifest, worker registry, `treehouse status`, worktree branch/HEAD, and Herdr snapshot. Preserve dirty or conflicted files. Restore never switches, resets, cleans, returns, or reallocates the worktree.

## Desk restore is partial

A successful `herdr pane run` only submits a command. Restore also requires that pane to report the exact Pi session and cwd with a usable status before changing registry IDs. Herdr may initially report Pi without its session identity; restore polls incomplete startup metadata until the bounded deadline, whose diagnostic includes the last transitional condition. A complete wrong identity still fails immediately. Correct the reported issue and run the same restore again. Handshaken live sessions are deduplicated, failed new tabs are closed on a best-effort basis, and the manifest remains under the XDG state directory with the previous save beside it.

## Installer destination differs

Inspect the existing launcher/extension. If replacement is intended, rerun `./install.sh --backup`; the old destination receives a UTC timestamp suffix. Never install a symlink from a disposable worktree.

## Extension changes do not appear

Confirm the extension is at `~/.pi/agent/extensions/pi-workers.ts`, `pi-worker` is on `PATH`, then use Pi's `/reload` or restart Pi.
