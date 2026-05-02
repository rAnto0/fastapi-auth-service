#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
example_file="$root_dir/.env.example"

if [[ ! -f "$example_file" ]]; then
  echo "Missing file: $example_file"
  exit 1
fi

for env in dev prod; do
  target="$root_dir/.env.$env"
  if [[ -f "$target" ]]; then
    echo "Exists: $target"
  else
    cp "$example_file" "$target"
    echo "Created: $target"
  fi
done
