# Orchestration workspace

This directory is a human-directed development desk, not an application repository or automated task queue.

At the start of an orchestrator session, read `ORCHESTRATION.md` and call `list_pi_workers`. Use the Pi worker tools rather than ad hoc Treehouse, Git, or Herdr setup. Preserve dirty worker worktrees and never force-return one unless the human explicitly asks to discard its uncommitted work.

The human decides what to discuss, start, review, merge, stop, or abandon. Do not add autonomous task claiming, queues, roles, stages, retries, budgets, or workflow state.
