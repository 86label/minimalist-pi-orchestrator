# Repository guide

This repository packages Minimalist Pi Orchestrator for Linux.

Keep the architecture deliberately small: a deterministic, testable host launcher, conservative desk recovery, and a thin typed Pi extension. It creates visible human-directed sessions; it must not grow task queues, workflow stages, automatic retries, role pipelines, autonomous task claiming, or a workflow database.

Never commit credentials, personal absolute paths, generated runtime state, host-specific operational notes, or repository-specific task content. Configuration examples must remain portable. Destructive worktree return must remain explicit and guarded.

The project is unsupported and does not accept contributions.
