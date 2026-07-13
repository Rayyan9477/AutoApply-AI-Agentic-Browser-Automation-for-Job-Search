#!/usr/bin/env bash
# Provision a fresh Hetzner / Oracle ARM box (Ubuntu 24.04) for AutoApply.
# Usage (as root):  REPO_URL=https://github.com/you/AutoApply.git bash bootstrap.sh
set -euo pipefail

REPO_URL="${REPO_URL:?set REPO_URL to your git remote}"
APP_DIR="${APP_DIR:-/root/autoapply}"

echo "==> Installing Docker + compose plugin"
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
ARCH="$(dpkg --print-architecture)"
CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"
echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

echo "==> Cloning the repo into ${APP_DIR}"
if [ -d "${APP_DIR}/.git" ]; then
  git -C "${APP_DIR}" pull
else
  git clone "${REPO_URL}" "${APP_DIR}"
fi
cd "${APP_DIR}"

if [ ! -f .env.prod ]; then
  cp .env.prod.example .env.prod
  echo "!!  Created .env.prod from the example — EDIT IT with real secrets before continuing:"
  echo "      nano ${APP_DIR}/.env.prod   (DATABASE_URL, AUTH__SECRET_KEY, SECRETS__APP_KEYS,"
  echo "      STORAGE__* for R2, METRICS_TOKEN, CORS_ORIGINS, DOMAIN)"
  echo "    Then run:  docker compose -f docker-compose.prod.yml up -d --build"
  exit 0
fi

echo "==> Building + starting the stack"
docker compose -f docker-compose.prod.yml up -d --build
echo "==> Running database migrations"
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
echo "==> Done. Check:  docker compose -f docker-compose.prod.yml ps"
