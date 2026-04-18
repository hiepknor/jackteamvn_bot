#!/bin/sh
set -eu

APP_USER="bot"
APP_GROUP="bot"
APP_DIRS="/app/data /app/logs /app/exports /app/storage"

ensure_runtime_dirs() {
  for dir in $APP_DIRS; do
    mkdir -p "$dir"
  done
}

fix_permissions_if_root() {
  if [ "$(id -u)" -ne 0 ]; then
    return 0
  fi

  # Ensure app user/group exist (defensive).
  if ! getent group "$APP_GROUP" >/dev/null 2>&1; then
    addgroup --system "$APP_GROUP" >/dev/null 2>&1 || true
  fi
  if ! id -u "$APP_USER" >/dev/null 2>&1; then
    adduser --system --ingroup "$APP_GROUP" "$APP_USER" >/dev/null 2>&1 || true
  fi

  for dir in $APP_DIRS; do
    chown -R "$APP_USER:$APP_GROUP" "$dir" 2>/dev/null || true
    chmod -R u+rwX "$dir" 2>/dev/null || true
  done
}

start_app() {
  if [ "$(id -u)" -eq 0 ]; then
    exec gosu "$APP_USER:$APP_GROUP" "$@"
  fi
  exec "$@"
}

ensure_runtime_dirs
fix_permissions_if_root
start_app "$@"
