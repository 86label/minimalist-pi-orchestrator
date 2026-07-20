#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./install.sh [--copy | --link] [--backup]

Installs pi-worker, pi-desk, and the Pi extension for the current user.
The default copies files. --link is intended only for development from a stable
checkout. Existing different targets are refused unless --backup is supplied.
Repository configuration is never overwritten.
EOF
}

mode=copy
backup=false
while (($#)); do
  case "$1" in
    --copy) mode=copy ;;
    --link) mode=link ;;
    --backup) backup=true ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

for executable in python3 git treehouse herdr pi; do
  command -v "$executable" >/dev/null 2>&1 || {
    printf 'error: required command not found on PATH: %s\n' "$executable" >&2
    exit 1
  }
done

root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
launcher_source="$root/bin/pi-worker"
desk_source="$root/bin/pi-desk"
extension_source="$root/src/pi-workers.ts"
launcher_target="${HOME:?HOME is required}/.local/bin/pi-worker"
desk_target="$HOME/.local/bin/pi-desk"
extension_target="$HOME/.pi/agent/extensions/minimalist-pi-orchestrator.ts"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/pi-worker"
config_target="$config_dir/repos.json"
example_target="$config_dir/repos.example.json"

install_one() {
  local source=$1 target=$2
  mkdir -p -- "$(dirname -- "$target")"

  if [[ $mode == link && -L $target && $(readlink "$target") == "$source" ]]; then
    printf 'unchanged %s -> %s\n' "$target" "$source"
    return
  fi
  if [[ $mode == copy && -f $target ]] && cmp -s -- "$source" "$target"; then
    printf 'unchanged %s\n' "$target"
    return
  fi
  if [[ -e $target || -L $target ]]; then
    if [[ $backup != true ]]; then
      printf 'error: %s already exists and differs; rerun with --backup\n' "$target" >&2
      exit 1
    fi
    local saved="${target}.bak.$(date -u +%Y%m%dT%H%M%SZ)"
    [[ ! -e $saved && ! -L $saved ]] || {
      printf 'error: backup exists: %s\n' "$saved" >&2
      exit 1
    }
    mv -- "$target" "$saved"
    printf 'backup %s\n' "$saved"
  fi

  if [[ $mode == link ]]; then
    ln -s -- "$source" "$target"
    printf 'linked %s -> %s\n' "$target" "$source"
  else
    cp -- "$source" "$target"
    printf 'copied %s\n' "$target"
  fi
}

install_one "$launcher_source" "$launcher_target"
install_one "$desk_source" "$desk_target"
install_one "$extension_source" "$extension_target"
chmod +x -- "$launcher_source" "$desk_source"
[[ $mode == link ]] || chmod +x -- "$launcher_target" "$desk_target"
mkdir -p -- "$config_dir"
cp -- "$root/config/repos.example.json" "$example_target"
if [[ ! -e $config_target ]]; then
  cp -- "$root/config/repos.example.json" "$config_target"
  chmod 0600 "$config_target"
  printf 'created %s; edit it before starting workers\n' "$config_target"
else
  printf 'preserved %s\n' "$config_target"
fi

case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) printf 'warning: add %s to PATH\n' "$HOME/.local/bin" >&2 ;;
esac
printf 'installation complete; restart Pi or run /reload\n'
