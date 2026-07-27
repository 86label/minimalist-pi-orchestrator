# Repository registration

`~/.config/pi-worker/repos.json` is an explicit allowlist (or `$XDG_CONFIG_HOME/pi-worker/repos.json` when set):

```json
{
  "default_repository": "example-app",
  "repositories": {
    "example-app": {
      "path": "~/projects/example-app",
      "remote": "origin",
      "default_branch": "main"
    }
  }
}
```

Keys are the names accepted by the Pi tool and `pi-worker start --repo`. `default_repository` is used when no name is supplied. Paths may use `~`; keep the real local paths in the untracked user configuration, not in this repository. `remote` and `default_branch` must identify the authoritative fresh base.

Registration is not discovery: an unlisted repository is rejected. Startup also fails closed if the configured branch cannot be fetched or resolved; it never silently starts from stale local state.
