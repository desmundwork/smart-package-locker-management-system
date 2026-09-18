#!/usr/bin/env bash
# =============================================================================
# apps/smart-locker-prod/deploy.sh
#
# Build + run the PRODUCTION Smart Package Locker on EC2 Ubuntu.
# Builds from the POC source + production auth overlay, then runs bound to
# 127.0.0.1:8100 behind Caddy (smart-locker.yeng.click + per-view subdomains).
#
# On first run, if .env is missing it is generated with a random JWT secret and
# random passwords for the three seed accounts, printed ONCE so you can save
# them.
#
# Usage (on the EC2 box):
#   sudo ./deploy.sh
# =============================================================================
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
	echo "ERROR: run this script as root (sudo)." >&2
	exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---- 1. Ensure Docker + compose plugin ----
if ! command -v docker >/dev/null 2>&1; then
	echo ">>> Installing Docker Engine..."
	export DEBIAN_FRONTEND=noninteractive
	apt-get update -y
	apt-get install -y ca-certificates curl
	install -m 0755 -d /etc/apt/keyrings
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
	chmod a+r /etc/apt/keyrings/docker.asc
	. /etc/os-release
	echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
		> /etc/apt/sources.list.d/docker.list
	apt-get update -y
	apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
	systemctl enable --now docker
fi
echo ">>> Docker: $(docker --version)"

# ---- 2. Generate .env with secrets on first run ----
if [[ ! -f .env ]]; then
	echo ">>> No .env found; generating one with random secrets..."
	gen() { openssl rand -hex 16; }
	JWT_SECRET="$(openssl rand -hex 32)"
	ADMIN_PW="$(gen)"
	AGENT_PW="$(gen)"
	CUSTOMER_PW="$(gen)"
	cat > .env <<EOF
JWT_SECRET=${JWT_SECRET}
ACCESS_TOKEN_TTL_MINUTES=60
SEED_ADMIN_USERNAME=admin
SEED_ADMIN_PASSWORD=${ADMIN_PW}
SEED_AGENT_USERNAME=agent
SEED_AGENT_PASSWORD=${AGENT_PW}
SEED_CUSTOMER_USERNAME=customer
SEED_CUSTOMER_PASSWORD=${CUSTOMER_PW}
STORAGE_UNIT_RATE=1
HOLD_TIMEOUT_SECONDS=120
EOF
	chmod 600 .env
	echo ""
	echo "  =========================================================="
	echo "  SAVE THESE CREDENTIALS NOW (shown once):"
	echo "    admin    / ${ADMIN_PW}"
	echo "    agent    / ${AGENT_PW}"
	echo "    customer / ${CUSTOMER_PW}"
	echo "  =========================================================="
	echo ""
fi

# ---- 3. Build + start ----
echo ">>> Building production image (from POC source + auth overlay)..."
docker compose build

echo ">>> Starting smart-locker-prod..."
docker compose up -d

sleep 3
docker compose ps

echo ""
echo ">>> Production app running on 127.0.0.1:8100 (loopback only)."
echo "    Landing : https://smart-locker.yeng.click"
echo "    Admin   : https://admin.smart-locker.yeng.click"
echo "    Agent   : https://agent.smart-locker.yeng.click"
echo "    Customer: https://customer.smart-locker.yeng.click"
echo "    Logs    : docker compose logs -f"
