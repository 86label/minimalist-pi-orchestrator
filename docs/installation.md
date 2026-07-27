# Installation

Install the documented prerequisites, clone a tagged release into a stable location, and run:

```bash
npm ci
npm run check
npm test
python3 -m unittest discover -s tests -v
./install.sh
```

The installer copies `pi-worker` and `pi-desk` to `~/.local/bin` and the Pi extension to `~/.pi/agent/extensions/minimalist-pi-orchestrator.ts`. It creates `repos.json` only when absent and refreshes `repos.example.json`. A repeated identical install is a no-op. A differing destination is refused unless `--backup` is explicit.

`./install.sh --link` is intended only for development from a stable primary checkout. Never link from a disposable Treehouse worktree.

`HOME` and `XDG_CONFIG_HOME` are honored, so copy installation can be tested under an isolated home when prerequisite commands are available on `PATH`.

## Optional orchestration workspace

The integration works from any Herdr workspace. For a dedicated desk, install the non-destructive [`templates/workspace/`](../templates/workspace/) context using the guarded procedure in [Human-directed orchestration](orchestration.md#installing-the-workspace-template). It refuses to replace existing workspace instructions.
