#!/usr/bin/env bash
# =============================================================================
# apps/smart-locker/deploy.sh
#
# Deploy the Smart Package Locker Management System on EC2 Ubuntu.
# Runs the published GHCR image via docker compose, bound to 127.0.0.1:8000
# so it is served ONLY through Caddy at https://smart-locker.yeng.click.
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

# ---- 1. Ensure Docker + compose plugin are installed ------------------------
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

# ---- 2. Pull the latest image ----------------------------------------------
echo ">>> Pulling latest smart-locker image..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" pull

# ---- 3. Start / update the service -----------------------------------------
echo ">>> Starting smart-locker..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d

sleep 3
docker compose -f "$SCRIPT_DIR/docker-compose.yml" ps

echo ""
echo ">>> smart-locker is running on 127.0.0.1:8000 (loopback only)."
echo "    Caddy serves it at: https://smart-locker.yeng.click"
echo "    Logs:   docker compose -f $SCRIPT_DIR/docker-compose.yml logs -f"
echo "    Update: sudo $SCRIPT_DIR/deploy.sh   (re-pulls + restarts)"
