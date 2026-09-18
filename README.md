# yeng.click

Workspace for hosting services under `*.yeng.click` behind a Caddy SSL
terminator on EC2 Ubuntu, with DNS on AWS Route 53.

## Structure

```
yengclick/
├── caddy/                     # SSL terminator + domain/DNS infrastructure
│   ├── Caddyfile              #   wildcard TLS + per-subdomain routing
│   ├── deploy.sh              #   builds Caddy (route53 module) + systemd
│   ├── setup-dns.sh           #   points apex + wildcard A records at EC2
│   ├── caddy.service          #   systemd unit
│   ├── caddy.env.example      #   ACME email + AWS creds template
│   └── iam-policy.json        #   least-privilege Route 53 IAM policy
│
└── apps/
    ├── smart-locker/          # POC  -> smart-locker-poc.yeng.click
    │   ├── docker-compose.yml #   runs the GHCR image on 127.0.0.1:8000
    │   ├── deploy.sh          #   installs Docker, pulls, starts
    │   └── README.md
    └── smart-locker-prod/     # PROD -> smart-locker.yeng.click (+ subdomains)
        ├── Dockerfile         #   builds from POC source + auth overlay
        ├── docker-compose.yml #   runs on 127.0.0.1:8100
        ├── deploy.sh          #   generates secrets, builds, starts
        ├── backend/app/       #   auth, RBAC, seeding, prod config/main
        ├── frontend/src/      #   login, per-view entry, authenticated API
        └── README.md          #   approach, design, trade-offs, improvements
```

## Environments

| Host | What |
|------|------|
| `smart-locker-poc.yeng.click` | the original POC, unchanged, all views open (`:8000`) |
| `smart-locker.yeng.click` | production landing / login (`:8100`) |
| `admin.smart-locker.yeng.click` | production Admin view (`ADMIN` role) |
| `agent.smart-locker.yeng.click` | production Agent view (`AGENT` role) |
| `customer.smart-locker.yeng.click` | production Customer view (`CUSTOMER` role) |

## How it fits together

Caddy issues **two wildcard certificates** via the Route 53 DNS-01 challenge:
`*.yeng.click` (covers `smart-locker`, `smart-locker-poc`, etc.) and
`*.smart-locker.yeng.click` (covers the third-level `admin/agent/customer`
production subdomains, which the first wildcard does NOT cover). Caddy
terminates TLS on 443 and reverse-proxies each subdomain to a loopback-bound
container, so apps are reachable only through Caddy.

```
                Internet (443/80)
                      │
                      ▼
            ┌──────────────────────┐
            │  Caddy (TLS term.)   │  *.yeng.click + *.smart-locker.yeng.click
            └──────────────────────┘
                      │ reverse_proxy by Host
        ┌─────────────┼───────────────────────────┐
        ▼             ▼                            ▼
  smart-locker-poc  smart-locker.yeng.click   admin/agent/customer.
  → :8000 (POC)     + subdomains → :8100       smart-locker.yeng.click → :8100
```

## Deploy order (on EC2 Ubuntu)

1. **DNS** — point the domain at the instance:
   ```bash
   cd caddy
   HOSTED_ZONE_ID=Z0123... ./setup-dns.sh
   ```

2. **Caddy** — build + start the SSL terminator:
   ```bash
   sudo HOSTED_ZONE_ID=Z0123... AWS_REGION=us-east-1 ACME_EMAIL=you@example.com ./deploy.sh
   ```

3. **POC app** — pull + run the container (served at `smart-locker-poc`):
   ```bash
   cd ../apps/smart-locker
   sudo ./deploy.sh
   ```

4. **Production app** — build + run (served at `smart-locker` + subdomains):
   ```bash
   cd ../smart-locker-prod
   sudo ./deploy.sh   # generates secrets on first run — save the printed creds
   ```

Then visit **https://smart-locker-poc.yeng.click** (POC) and
**https://smart-locker.yeng.click** (production).

## Adding another app

1. Create `apps/<name>/` with its own `docker-compose.yml` bound to
   `127.0.0.1:<port>`.
2. Add a route in `caddy/Caddyfile`:
   ```
   @<name> host <name>.yeng.click
   handle @<name> {
       reverse_proxy 127.0.0.1:<port>
   }
   ```
3. `sudo systemctl reload caddy`.

No new certificate or DNS record is needed — the wildcard cert and wildcard
A record already cover every subdomain.

## Prerequisites

- EC2 Ubuntu (22.04 / 24.04), security group allowing inbound **80** + **443**
- Route 53 hosted zone for `yeng.click`
- AWS credentials (IAM instance role recommended) with the permissions in
  `caddy/iam-policy.json`
- Docker (installed automatically by the app deploy scripts if missing)

## Secrets

Secrets are never committed — `.gitignore` excludes all `.env` files (except
`*.env.example` templates) and `caddy/caddy.env`. The production app's
`deploy.sh` generates `apps/smart-locker-prod/.env` with a random `JWT_SECRET`
and random seed passwords on first run, printing the credentials once.

See `caddy/`, `apps/smart-locker/`, and `apps/smart-locker-prod/` for
component-level details.
