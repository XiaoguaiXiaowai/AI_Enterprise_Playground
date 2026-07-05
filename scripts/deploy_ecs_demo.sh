#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_APP_DIR="$HOME/apps/aep"
if [ -f "$SCRIPT_DIR/../docker-compose.demo.yml" ]; then
  DEFAULT_APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

DOMAIN="${DOMAIN:-playground.pangliantagege.top}"
EMAIL="${EMAIL:-}"
APP_DIR="${APP_DIR:-$DEFAULT_APP_DIR}"
REPO_URL="${REPO_URL:-}"
BRANCH="${BRANCH:-main}"
ENABLE_HTTPS="${ENABLE_HTTPS:-1}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1
}

apt_install() {
  sudo apt-get update -y
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "$@"
}

ensure_base() {
  apt_install ca-certificates curl gnupg lsb-release git openssl nginx
}

ensure_docker() {
  if require_cmd docker && docker compose version >/dev/null 2>&1; then
    return 0
  fi

  sudo install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
  fi

  if [ ! -f /etc/apt/sources.list.d/docker.list ]; then
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  fi

  sudo apt-get update -y
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable --now docker
}

ensure_app_dir() {
  mkdir -p "$APP_DIR"
  cd "$APP_DIR"
  if [ ! -d ".git" ]; then
    if [ -n "$REPO_URL" ]; then
      cd ..
      rm -rf "$APP_DIR"
      git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
      cd "$APP_DIR"
    else
      if [ ! -f docker-compose.demo.yml ] || [ ! -f .env.example ]; then
        echo "APP_DIR is not a valid project directory: $APP_DIR"
        echo "Expected files: docker-compose.demo.yml and .env.example"
        exit 1
      fi
      return 0
    fi
  fi

  git fetch --all --prune
  git checkout "$BRANCH"
  git pull --ff-only origin "$BRANCH"
}

ensure_env() {
  cd "$APP_DIR"
  if [ ! -f .env ]; then
    cp .env.example .env
  fi

  if grep -q '^JWT_SECRET_KEY=dev-secret$' .env || ! grep -q '^JWT_SECRET_KEY=' .env; then
    JWT_SECRET_KEY="$(openssl rand -hex 32)"
    if grep -q '^JWT_SECRET_KEY=' .env; then
      sed -i "s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=${JWT_SECRET_KEY}/" .env
    else
      echo "JWT_SECRET_KEY=${JWT_SECRET_KEY}" >> .env
    fi
  fi

  if grep -q '^SESSION_SECRET_KEY=dev-session-secret$' .env || ! grep -q '^SESSION_SECRET_KEY=' .env; then
    SESSION_SECRET_KEY="$(openssl rand -hex 32)"
    if grep -q '^SESSION_SECRET_KEY=' .env; then
      sed -i "s/^SESSION_SECRET_KEY=.*/SESSION_SECRET_KEY=${SESSION_SECRET_KEY}/" .env
    else
      echo "SESSION_SECRET_KEY=${SESSION_SECRET_KEY}" >> .env
    fi
  fi

  if grep -q '^ENVIRONMENT=' .env; then
    sed -i 's/^ENVIRONMENT=.*/ENVIRONMENT=prod/' .env
  else
    echo "ENVIRONMENT=prod" >> .env
  fi

  if grep -q '^CHROMA_PERSIST_DIR=' .env; then
    sed -i 's|^CHROMA_PERSIST_DIR=.*|CHROMA_PERSIST_DIR=/data/chroma|' .env
  else
    echo "CHROMA_PERSIST_DIR=/data/chroma" >> .env
  fi

  if grep -q '^UPLOADS_DIR=' .env; then
    sed -i 's|^UPLOADS_DIR=.*|UPLOADS_DIR=/data/uploads|' .env
  else
    echo "UPLOADS_DIR=/data/uploads" >> .env
  fi
}

write_nginx() {
  local conf="/etc/nginx/sites-available/aep-playground.conf"
  local enabled="/etc/nginx/sites-enabled/aep-playground.conf"

  local existing
  existing="$(sudo grep -R "server_name\s\+.*\b${DOMAIN}\b" /etc/nginx/sites-enabled 2>/dev/null || true)"
  if [ -n "$existing" ] && ! echo "$existing" | grep -q "aep-playground.conf"; then
    echo "DOMAIN already configured in nginx, refusing to override:"
    echo "$existing"
    exit 1
  fi

  sudo tee "$conf" >/dev/null <<EOF
limit_req_zone \$binary_remote_addr zone=authlimit:10m rate=5r/m;

server {
  server_name ${DOMAIN};

  location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host \$host;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }

  location /api/ {
    proxy_pass http://127.0.0.1:8000/api/;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
  }

  location = /docs { proxy_pass http://127.0.0.1:8000/docs; }
  location = /openapi.json { proxy_pass http://127.0.0.1:8000/openapi.json; }
  location = /health { proxy_pass http://127.0.0.1:8000/health; }

  location /ws {
    proxy_pass http://127.0.0.1:8000/ws;
    proxy_http_version 1.1;
    proxy_set_header Upgrade \$http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host \$host;
  }

  location = /auth/register {
    limit_req zone=authlimit burst=20 nodelay;
    proxy_pass http://127.0.0.1:8000/auth/register;
  }

  location = /auth/login {
    limit_req zone=authlimit burst=40 nodelay;
    proxy_pass http://127.0.0.1:8000/auth/login;
  }

  location = /api/v1/auth/register {
    limit_req zone=authlimit burst=20 nodelay;
    proxy_pass http://127.0.0.1:8000/api/v1/auth/register;
  }

  location = /api/v1/auth/login {
    limit_req zone=authlimit burst=40 nodelay;
    proxy_pass http://127.0.0.1:8000/api/v1/auth/login;
  }
}
EOF

  if [ ! -f "$enabled" ]; then
    sudo ln -s "$conf" "$enabled"
  fi

  sudo nginx -t
  sudo systemctl reload nginx
}

ensure_https() {
  if [ "$ENABLE_HTTPS" != "1" ]; then
    return 0
  fi

  if [ -z "$EMAIL" ]; then
    echo "EMAIL is required when ENABLE_HTTPS=1"
    exit 1
  fi

  apt_install certbot python3-certbot-nginx
  sudo certbot --nginx -d "$DOMAIN" -m "$EMAIL" --agree-tos --non-interactive --redirect || true
  sudo systemctl reload nginx
}

start_services() {
  cd "$APP_DIR"
  sudo docker compose -f docker-compose.demo.yml up --build -d
  sudo docker compose -f docker-compose.demo.yml ps
}

main() {
  echo "Deploying to $(hostname) for domain: $DOMAIN"
  ensure_base
  ensure_docker
  ensure_app_dir
  ensure_env
  write_nginx
  ensure_https
  start_services
  echo "Done"
  echo "Frontend: https://${DOMAIN}/dashboard"
  echo "Backend docs: https://${DOMAIN}/docs"
}

main
