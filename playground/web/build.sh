#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/dist"

if ! command -v zig >/dev/null; then echo "zig not found!"; exit 1; fi

mkdir -p "$OUT"
zig cc -target mips-linux-musleabi -O2 -static "$HERE/httpd.c" -o "$OUT/httpd"
command -v llvm-strip >/dev/null && llvm-strip --strip-all "$OUT/httpd" || true

cp "$HERE/index.html" "$OUT"/
