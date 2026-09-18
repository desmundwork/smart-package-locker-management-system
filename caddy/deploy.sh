#!/usr/bin/env bash
# =============================================================================
# deploy.sh - Install Caddy (with Route 53 DNS module) as an SSL terminator
#             for *.yeng.click on an EC2 Ubuntu host.
#
# Usage (run as root / with sudo on the EC2 box):
#   sudo HOSTED_ZONE_ID=Z0123... AWS_REGION=us-east-1 ACME_EMAIL=you@x.com \
#        ./deploy.sh
#
# Optional (Option B - static keys instead of instance role):
#   AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
# =============================================================================
set -euo pipefail

# ---- Config / input validation ---------------------------------------------
ACME_EMAIL="${ACME_EMAIL:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"
HOSTED_ZONE_ID="${HOSTED_ZONE_ID:-}"
GO_VERSION="1.22.5"

if [[ $EUID -ne 0 ]]; then
	echo "ERROR: run this script as root (sudo)." >&2
	exit 1
fi

if [[ -z "$ACME_EMAIL" ]]; then
	echo "ERROR: ACME_EMAIL is required (email for Let's Encrypt)." >&2
	exit 1
fi

echo ">>> Deploying Caddy SSL terminator for *.yeng.click"
echo "    ACME_EMAIL   = $ACME_EMAIL"
echo "    AWS_REGION   = $AWS_REGION"
echo "    HOSTED_ZONE  = ${HOSTED_ZONE_ID:-<using instance role / not set>}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- 1. System deps ---------------------------------------------------------
echo ">>> Installing system dependencies..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl tar ca-certificates debian-keyring debian-archive-keyring apt-transport-https

# ---- 2. Install Go (needed by xcaddy to build the custom binary) ------------
if ! command -v go >/dev/null 2>&1 || ! go version 2>/dev/null | grep -q "$GO_VERSION"; then
	echo ">>> Installing Go ${GO_VERSION}..."
	ARCH="$(dpkg --print-architecture)"
	case "$ARCH" in
		amd64) GOARCH="amd64" ;;
		arm64) GOARCH="arm64" ;;
		*) echo "Unsupported arch: $ARCH" >&2; exit 1 ;;
	esac
	curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${GOARCH}.tar.gz" -o /tmp/go.tgz
	rm -rf /usr/local/go
	tar -C /usr/local -xzf /tmp/go.tgz
	rm -f /tmp/go.tgz
fi
export PATH="/usr/local/go/bin:${PATH}:/root/go/bin"

# ---- 3. Build Caddy with the Route 53 DNS module via xcaddy -----------------
echo ">>> Installing xcaddy and building Caddy with route53 module..."
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest

# Build the custom binary (includes DNS-01 provider for Route 53).
TMP_BUILD="$(mktemp -d)"
pushd "$TMP_BUILD" >/dev/null
/root/go/bin/xcaddy build \
	--with github.com/caddy-dns/route53
popd >/dev/null

install -m 0755 "$TMP_BUILD/caddy" /usr/bin/caddy
rm -rf "$TMP_BUILD"
echo ">>> Caddy version: $(/usr/bin/caddy version)"

# ---- 4. Create caddy user, dirs ---------------------------------------------
echo ">>> Creating caddy user and directories..."
id -u caddy >/dev/null 2>&1 || useradd --system --home /var/lib/caddy --shell /usr/sbin/nologin caddy
mkdir -p /etc/caddy /var/log/caddy /var/lib/caddy
chown -R caddy:caddy /var/log/caddy /var/lib/caddy

# ---- 5. Install Caddyfile ---------------------------------------------------
echo ">>> Installing Caddyfile..."
install -m 0644 "$SCRIPT_DIR/Caddyfile" /etc/caddy/Caddyfile

# ---- 6. Install env file ----------------------------------------------------
echo ">>> Writing /etc/caddy/caddy.env..."
{
	echo "ACME_EMAIL=${ACME_EMAIL}"
	echo "AWS_REGION=${AWS_REGION}"
	if [[ -n "${AWS_ACCESS_KEY_ID:-}" && -n "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
		echo "AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}"
		echo "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}"
	fi
} > /etc/caddy/caddy.env
chown root:caddy /etc/caddy/caddy.env
chmod 640 /etc/caddy/caddy.env

# ---- 7. Install systemd unit ------------------------------------------------
echo ">>> Installing systemd service..."
install -m 0644 "$SCRIPT_DIR/caddy.service" /etc/systemd/system/caddy.service

# ---- 8. Validate config, start service --------------------------------------
echo ">>> Validating Caddyfile..."
AWS_REGION="$AWS_REGION" ACME_EMAIL="$ACME_EMAIL" \
	/usr/bin/caddy validate --config /etc/caddy/Caddyfile

echo ">>> Enabling and starting Caddy..."
systemctl daemon-reload
systemctl enable caddy
systemctl restart caddy

sleep 3
systemctl --no-pager status caddy || true

echo ""
echo ">>> Done. Caddy is running as the SSL terminator for *.yeng.click"
echo "    - Check certs:  journalctl -u caddy -f"
echo "    - Edit routes:  /etc/caddy/Caddyfile  then  sudo systemctl reload caddy"
