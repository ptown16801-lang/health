#!/usr/bin/env bash
set -euo pipefail

# Prevent host Python path entries from contaminating the isolated environment.
unset PYTHONPATH

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
private_root="${JON107_PRIVATE_ROOT:-$repo_root/.private}"
source_dir="$private_root/tools/onenote-tool"
venv_dir="$private_root/tools/venv"
expected_commit=abd2065c28a2dcfd45edcc944d8be078c313dd02
repository=https://github.com/vanarebane/onenote-tool.git

umask 077
mkdir -p "$private_root/tools"

if [[ ! -d "$source_dir/.git" ]]; then
  git clone --filter=blob:none "$repository" "$source_dir"
fi
git -C "$source_dir" fetch --depth 1 origin "$expected_commit"
git -C "$source_dir" checkout --detach "$expected_commit"
actual_commit=$(git -C "$source_dir" rev-parse HEAD)
if [[ "$actual_commit" != "$expected_commit" ]]; then
  echo "Refusing installation: expected $expected_commit, got $actual_commit" >&2
  exit 1
fi

python_bin="${PYTHON_BIN:-python3}"
if ! "$python_bin" -m venv "$venv_dir"; then
  echo "Python venv support is required. Install the repository-pinned Python with mise or provide PYTHON_BIN." >&2
  exit 1
fi
"$venv_dir/bin/python" -m pip install --disable-pip-version-check "$source_dir[cli]"

installed_version=$(
  "$venv_dir/bin/python" -c 'import importlib.metadata; print(importlib.metadata.version("onenote-tool"))'
)
parser_version=$(
  "$venv_dir/bin/python" -c 'import importlib.metadata; print(importlib.metadata.version("pyOneNote"))'
)
if [[ "$installed_version" != "0.1.5" ]]; then
  echo "Refusing installation: expected onenote-tool 0.1.5, got $installed_version" >&2
  exit 1
fi
if [[ "$parser_version" != "0.0.2" ]]; then
  echo "Refusing installation: expected pyOneNote 0.0.2, got $parser_version" >&2
  exit 1
fi

echo "Installed onenote-tool $installed_version with pyOneNote $parser_version from verified commit $actual_commit in $venv_dir"
