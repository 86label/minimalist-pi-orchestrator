# Human-directed orchestration

A Pi session in a workspace can act as the conversational orchestrator while visible worker Pi sessions run in independent Herdr tabs and isolated Treehouse worktrees. These are cooperation conventions, not workflow automation. The human decides what to discuss, create, direct, review, merge, stop, or abandon.

A ready-to-copy workspace context is in [`templates/workspace/`](../templates/workspace/).

## Sources of truth and separation

The workspace `AGENTS.md` routes Pi to `ORCHESTRATION.md`, which owns human-facing operating judgment. The global `src/pi-workers.ts` extension is only a typed adapter to `pi-worker`. Herdr owns live Pi identity and status, while `pi-worker` owns deterministic host lifecycle mechanics.

Managed workers carry `PI_WORKER_NAME`, receive no orchestration tools, and are refused by `pi-worker start`. This prevents accidental nested orchestration; it is not a security boundary. When decomposition is useful, the human can ask the orchestrator to create sibling workers.

## Starting or resuming

At the start of an orchestrator session:

1. Read the workspace instructions.
2. Call `list_pi_workers` to recover recorded identities and conservative status.
3. Use `inspect_pi_worker` only when needed to reconcile a worker or understand progress.
4. Ask the human what to resume when intent is unclear.

Conversation state is useful but not authoritative. Git owns branches and commits, Treehouse owns leases, Herdr owns the live desk, Pi owns conversations, and the worker registry connects them.

## Natural-language session creation

Interpret ordinary requests conversationally; do not require magic commands.

- “Open a tab for me” normally means an empty human-led Pi with no prompt and `focus=true`.
- “Delegate this” normally means a non-focused worker with a self-contained prompt.
- Summarize agreed objectives, decisions, constraints, acceptance criteria, and open questions without inventing requirements.
- Pass through a requested model; otherwise use Pi's configured default.
- Omit the repository when the configured default applies.

Use `spawn_pi_worker`, not ad hoc Treehouse, Git, or Herdr setup. Every worker receives its own tab.

## Observation and communication

Prefer the typed worker tools:

- `list_pi_workers` gives bounded status for recorded workers;
- `inspect_pi_worker` gives exact identity, recent output, and Git/lease/PR evidence;
- `send_pi_worker_follow_up` types one short follow-up and submits Enter once;
- `focus_pi_worker` transfers the human to the exact recorded tab;
- `resume_pi_worker` resumes only a reconciled exact session in its recorded pane;
- `restore_pi_workers` recreates all missing managed workers from durable records without a desk save.

Do not poll continuously. Idle status is not proof of completion; inspect relevant output and durable Git evidence. Missing or ambiguous identity is a reason to stop and reconcile, not to guess or allocate a replacement.

## Restoring managed workers and the optional full desk

Managed workers use deterministic private Pi session storage. After a restart, use `restore_pi_workers` (or `pi-worker restore-all`) to recreate missing managed tabs directly from registry, session, worktree, branch, and lease identity. No prior save is required.

Use `pi-desk save NAME` only when the human also wants the orchestrator conversation, unmanaged tabs, workspace label, order, and focus preserved. Exit Pi normally after saving so session files flush, then run `pi-desk restore NAME` from an ordinary Herdr shell after restart.

Never make either restore path pass by cleaning, resetting, switching, reallocating, or force-returning work. Correct identity discrepancies conservatively and retry.

## Return and recovery

After work is integrated or deliberately abandoned, call `return_pi_worker`. Return refuses dirty worktrees by default. `force=true` requires explicit interactive human confirmation and deliberately discards uncommitted changes. A normal return removes the active registry record and lease while retaining both the branch and private Pi transcript. Transcript deletion is a separate explicit retention decision.

Reconcile records conservatively:

- registry entry plus missing tab: inspect the worktree and branch;
- visible tab plus missing registry: inspect cwd, branch, and lease holder;
- exited Pi plus durable lease: preserve it until the human chooses resume or return;
- dirty or conflicted worktree: preserve it and surface the issue;
- legacy worker sharing the orchestrator tab: close only its pane;
- never delete locks, holder metadata, branches, or worktrees merely because they appear stale.

## Boundaries

The integration may create, inspect, message, focus, resume, and safely return visible workers. It must not grow autonomous task consumption, task queues, automatic dispatch, role pipelines, mandatory stages, retries, token budgets, or a workflow database.

## Installing the workspace template

Copy the template only when neither destination file exists:

```bash
WORKSPACE="$HOME/development-desk"
mkdir -p "$WORKSPACE"
for file in AGENTS.md ORCHESTRATION.md; do
  if [ -e "$WORKSPACE/$file" ]; then
    printf 'refusing to overwrite %s\n' "$WORKSPACE/$file" >&2
    exit 1
  fi
done
for file in AGENTS.md ORCHESTRATION.md; do
  install -m 0644 "templates/workspace/$file" "$WORKSPACE/$file"
done
```

Run this from the stable repository checkout and adapt the copied operating model to the workspace without adding autonomous behavior.
