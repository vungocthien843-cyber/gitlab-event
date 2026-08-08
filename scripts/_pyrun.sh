#!/usr/bin/env bash
# Cross-platform Python launcher for AI log hooks.
# Tries python3 → python → py -3 on PATH; on Windows, falls back to common
# Python install locations because Git Bash launched by some hooks gets a
# stripped PATH that omits the Windows Python directory.
#
# On Windows, `python`/`python3` on PATH can resolve to the Microsoft Store's
# "App Execution Alias" stub instead of a real interpreter. That stub is
# still found by `command -v` (it exists on PATH), but running it just prints
# an install prompt and exits non-zero — so every candidate is verified with
# `--version` before being trusted, not merely checked for presence.
#
# Designed to be sourced or called as: bash scripts/_pyrun.sh <script> [args...]
#
# Exits 0 silently if no Python is found — hooks must never block the AI tool.
set -u

is_real_python() {
  "$@" --version >/dev/null 2>&1
}

PY=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && is_real_python "$cand"; then
    PY="$cand"
    break
  fi
done

if [ -z "$PY" ] && command -v py >/dev/null 2>&1 && is_real_python py -3; then
  PY="py -3"
fi

if [ -z "$PY" ]; then
  # PATH candidates missing or all Windows Store stubs — probe the project's
  # own venv and standard install locations directly.
  shopt -s nullglob 2>/dev/null || true
  for cand in \
    .venv/Scripts/python.exe \
    venv/Scripts/python.exe \
    /c/Users/*/AppData/Local/Programs/Python/Python*/python.exe \
    "/c/Program Files/Python"*/python.exe \
    "/c/Program Files (x86)/Python"*/python.exe \
    /c/Python*/python.exe; do
    if [ -x "$cand" ] && is_real_python "$cand"; then PY="$cand"; break; fi
  done
  shopt -u nullglob 2>/dev/null || true
fi

[ -n "$PY" ] || exit 0

# shellcheck disable=SC2086
exec $PY "$@"
