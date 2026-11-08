#!/usr/bin/env bash
# Tests fuer die Offline-Warteschlange. Kein Testrahmen im Frontend: esbuild
# (kommt mit vite) buendelt den Test samt warteschlange.ts, node:test fuehrt aus.
set -euo pipefail
hier="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
aus="$(mktemp -d)"
trap 'rm -rf "$aus"' EXIT
"$hier/../node_modules/.bin/esbuild" "$hier/warteschlange.test.ts" --bundle \
  --platform=node --format=esm --log-level=warning --outfile="$aus/test.mjs"
node --test "$aus/test.mjs"
