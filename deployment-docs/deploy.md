# Deploy

Publish the image to GitHub Container Registry (GHCR) as a **public** image, then pull and run it on an Ubuntu host with Docker.

> This project is already published at
> `ghcr.io/desmundwork/smart-package-locker-management-system` (tags `0.1.0`,
> `latest`). The steps below document how that was done and how to release new
> versions.

## Variables

```bash
export OWNER=desmundwork                  # GitHub org that owns the package
export IMAGE=ghcr.io/$OWNER/smart-package-locker-management-system
export TAG=0.1.0
```

---

## 1. Push to GHCR (from your build machine)

### 1.1 Create a token

Create a GitHub Personal Access Token (classic) with the `write:packages` scope (this also grants `read:packages`). Store it securely; do not commit it.

```bash
export CR_PAT=your-token-here
```

### 1.2 Log in to GHCR

```bash
echo "$CR_PAT" | docker login ghcr.io -u "$OWNER" --password-stdin
```

### 1.3 Build (if not already built) and push

```bash
docker build -t $IMAGE:$TAG -t $IMAGE:latest .
docker push $IMAGE:$TAG
docker push $IMAGE:latest
```

### 1.4 Make the package public

By default a new GHCR package is private, and GitHub has **no REST API** to
change container-package visibility — it must be done in the web UI:

1. Open the package settings:
   `https://github.com/orgs/desmundwork/packages/container/smart-package-locker-management-system/settings`
2. Under **Danger Zone → Change visibility**, set it to **Public**.

Once public, no login is needed to pull.

---

## 2. Pull and run on Ubuntu

On a fresh Ubuntu host (20.04 / 22.04 / 24.04).

### 2.1 Install Docker (once)

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
sudo systemctl enable --now docker
```

(Optional, run docker without sudo:)

```bash
sudo usermod -aG docker $USER && newgrp docker
```

### 2.2 Pull the public image

Because the package is public, no login is required:

```bash
export OWNER=your-github-username
export IMAGE=ghcr.io/$OWNER/smart-package-locker
export TAG=0.1.0
docker pull $IMAGE:$TAG
```

### 2.3 Run

```bash
docker run -d --name locker \
  --restart unless-stopped \
  -p 80:8000 \
  -v locker-data:/data \
  -e DATABASE_URL="sqlite:////data/locker.db" \
  $IMAGE:$TAG
```

The app is now on `http://<server-ip>/` (admin at `/admin`, agent at `/agent`, customer at `/customer`).

### 2.4 Verify

```bash
curl -s http://localhost/api/health
docker logs -f locker
```

---

## 3. Update to a new version

```bash
docker pull $IMAGE:<new-tag>
docker stop locker && docker rm locker
docker run -d --name locker --restart unless-stopped -p 80:8000 \
  -v locker-data:/data -e DATABASE_URL="sqlite:////data/locker.db" \
  $IMAGE:<new-tag>
```

## Notes

- The `-v locker-data:/data` volume preserves the SQLite database across updates.
- For production, put a reverse proxy (nginx / Caddy) in front for TLS, and consider moving `DATABASE_URL` to Postgres (see `tech-stack.md`).
- Never bake the `CR_PAT` into the image or commit it to the repo.
