#!/usr/bin/env bash
set -Eeuo pipefail

# =========================
# Config
# =========================
REPO_URL="https://github.com/hiepknor/jackteamvn_bot.git"
BRANCH="master"
APP_DIR="/opt/jackteamvn_bot/app"
ENV_FILE="$APP_DIR/.env"

# =========================
# Helpers
# =========================
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Thiếu lệnh: $1"
    exit 1
  }
}

docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    echo "Không tìm thấy docker compose / docker-compose"
    exit 1
  fi
}

cleanup_on_error() {
  echo
  echo "Deploy thất bại."
  echo "Xem log container bằng lệnh:"
  echo "  cd $APP_DIR && $(compose_cmd_string) logs --tail=200"
}
trap cleanup_on_error ERR

compose_cmd_string() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
  else
    echo "docker-compose"
  fi
}

# =========================
# Check dependencies
# =========================
need_cmd git
need_cmd docker

# =========================
# Prepare app directory
# =========================
sudo mkdir -p "$APP_DIR"
sudo chown -R "$USER":"$USER" "$(dirname "$APP_DIR")"

if [ ! -d "$APP_DIR/.git" ]; then
  log "Cloning repo..."
  rm -rf "$APP_DIR"
  git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  log "Repo already exists."
fi

cd "$APP_DIR"

# =========================
# Update source code
# =========================
log "Fetching latest code..."
git fetch origin "$BRANCH"
git checkout "$BRANCH"

LOCAL_SHA="$(git rev-parse HEAD || true)"
REMOTE_SHA="$(git rev-parse "origin/$BRANCH")"

if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]; then
  log "Updating code to latest commit..."
  git reset --hard "origin/$BRANCH"
else
  log "Code is already up to date."
fi

# =========================
# Prepare environment
# =========================
if [ ! -f "$ENV_FILE" ]; then
  log "Creating .env from .env.example ..."
  cp .env.example .env

  echo
  echo "=================================================="
  echo "Lần chạy đầu: hãy sửa file $ENV_FILE"
  echo "Ít nhất cần sửa: BOT_TOKEN"
  echo "Có thể sửa thêm: ADMIN_IDS, BOT_NAME..."
  echo "Sau khi sửa xong, chạy lại file này:"
  echo "  bash $0"
  echo "=================================================="
  exit 0
fi

if grep -q "BOT_TOKEN=your_bot_token_here" "$ENV_FILE" || ! grep -q '^BOT_TOKEN=' "$ENV_FILE"; then
  echo
  echo "BOT_TOKEN trong $ENV_FILE chưa được cấu hình đúng."
  echo "Hãy mở file ra sửa rồi chạy lại:"
  echo "  nano $ENV_FILE"
  echo "  bash $0"
  exit 1
fi

# =========================
# Ensure persistent dirs
# =========================
mkdir -p data logs exports storage

# =========================
# Deploy with Docker Compose
# =========================
log "Building and starting containers..."
docker_compose down --remove-orphans || true
docker_compose up -d --build

# =========================
# Show status
# =========================
log "Container status:"
docker_compose ps

log "Recent logs:"
docker_compose logs --tail=50

echo
echo "Deploy hoàn tất."
echo "Mỗi lần sửa code ở local:"
echo "1) git add . && git commit -m 'update' && git push"
echo "2) SSH vào VPS và chạy lại:"
echo "   bash $0"