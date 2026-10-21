#!/usr/bin/env bash
# MixYard ships no package manifest or lockfile. Confirm the static-server runtime and exit.
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to serve MixYard" >&2
  exit 1
fi

python3 -c 'import http.server'
echo "MixYard has no dependencies to install."
