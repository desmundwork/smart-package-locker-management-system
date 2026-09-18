#!/usr/bin/env bash
# =============================================================================
# setup-dns.sh - Create/Update Route 53 records so yeng.click and *.yeng.click
#                point at this EC2 instance.
#
# This gives you "subdomains for all under *.yeng.click": a single wildcard
# A record means ANY subdomain (foo.yeng.click, bar.yeng.click, ...) resolves
# to this box, and Caddy then terminates SSL + routes based on the Host.
#
# Requires the AWS CLI configured with permission to change the zone.
#
# Usage:
#   HOSTED_ZONE_ID=Z0123... ./setup-dns.sh [PUBLIC_IP]
#
# If PUBLIC_IP is omitted, it is auto-detected from EC2 instance metadata.
# =============================================================================
set -euo pipefail

HOSTED_ZONE_ID="${HOSTED_ZONE_ID:-}"
TTL="${TTL:-300}"

if [[ -z "$HOSTED_ZONE_ID" ]]; then
	echo "ERROR: HOSTED_ZONE_ID is required." >&2
	exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
	echo "ERROR: aws CLI not found. Install it first: 'sudo snap install aws-cli --classic'" >&2
	exit 1
fi

# ---- Resolve the public IP --------------------------------------------------
PUBLIC_IP="${1:-}"
if [[ -z "$PUBLIC_IP" ]]; then
	echo ">>> Auto-detecting EC2 public IP via IMDSv2..."
	TOKEN="$(curl -sf -X PUT "http://169.254.169.254/latest/api/token" \
		-H "X-aws-ec2-metadata-token-ttl-seconds: 300" || true)"
	if [[ -n "$TOKEN" ]]; then
		PUBLIC_IP="$(curl -sf -H "X-aws-ec2-metadata-token: $TOKEN" \
			http://169.254.169.254/latest/meta-data/public-ipv4 || true)"
	fi
fi

if [[ -z "$PUBLIC_IP" ]]; then
	echo "ERROR: could not determine public IP. Pass it explicitly:" >&2
	echo "  HOSTED_ZONE_ID=$HOSTED_ZONE_ID ./setup-dns.sh 1.2.3.4" >&2
	exit 1
fi

echo ">>> Pointing yeng.click, *.yeng.click and *.smart-locker.yeng.click -> $PUBLIC_IP (TTL ${TTL}s)"

# ---- Build the change batch (apex + wildcard) -------------------------------
CHANGE_BATCH="$(cat <<JSON
{
  "Comment": "Point apex and wildcard at EC2 for Caddy SSL termination",
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "yeng.click",
        "Type": "A",
        "TTL": ${TTL},
        "ResourceRecords": [{ "Value": "${PUBLIC_IP}" }]
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "*.yeng.click",
        "Type": "A",
        "TTL": ${TTL},
        "ResourceRecords": [{ "Value": "${PUBLIC_IP}" }]
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "*.smart-locker.yeng.click",
        "Type": "A",
        "TTL": ${TTL},
        "ResourceRecords": [{ "Value": "${PUBLIC_IP}" }]
      }
    }
  ]
}
JSON
)"

CHANGE_ID="$(aws route53 change-resource-record-sets \
	--hosted-zone-id "$HOSTED_ZONE_ID" \
	--change-batch "$CHANGE_BATCH" \
	--query 'ChangeInfo.Id' --output text)"

echo ">>> Submitted change: $CHANGE_ID"
echo ">>> Waiting for INSYNC (DNS propagation within Route 53)..."
aws route53 wait resource-record-sets-changed --id "$CHANGE_ID"

echo ">>> DNS records are live."
echo "    Test:  dig +short foo.yeng.click   # should return $PUBLIC_IP"
