#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SUB="$HERE/doom-ascii"
OUT="$HERE/dist"
ZIG_TARGET="mips-linux-musleabi" # BE, softfloat

if ! command -v zig >/dev/null; then echo "zig not found!"; exit 1; fi

git -C "$HERE" submodule update --init "$SUB"

make -C "$SUB" PLATFORM=musl clean >/dev/null
make -C "$SUB" PLATFORM=musl CC="zig cc -target $ZIG_TARGET"
BIN="$SUB/_musl/game/doom-ascii"

if command -v llvm-strip >/dev/null; then llvm-strip --strip-all "$BIN"; else echo "llvm-strip not found, binary not stripped"; fi

mkdir -p "$OUT"
cp "$BIN" "$OUT/doom"
cp "$HERE"/wad/* "$OUT"/
