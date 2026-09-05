# Docker Quickstart

Docker Compose is the supported way to run Duck Monitoring. One command starts Postgres, Redis, the API, Celery, and the UI.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose V2 (`docker compose version`)

## Start

From the repo root:

```bash
./scripts/docker-up.sh
```

That will:

1. Create `.env` from `.env.example` if you do not have one (and generate a `SECRET_KEY`)
2. Build images and start the stack
3. Run migrations on boot

Open **http://localhost:3000** and complete first-time admin setup.

```bash
./scripts/docker-up.sh --rebuild   # force image rebuild
./scripts/docker-up.sh --reset     # wipe volumes (destroys data)
./scripts/docker-down.sh           # stop, keep data
./scripts/docker-down.sh --wipe    # stop and delete volumes
```

Equivalent Compose commands:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f backend
docker compose down
```

## What you get

| URL | Purpose |
|---|---|
| http://localhost:3000 | Web UI |
| http://localhost:3000/api/health/ | API health (proxied) |
| http://localhost:3000/admin/ | Django admin |

The browser talks to the UI only. Nginx proxies `/api`, `/static`, and `/admin` to the backend. You do not need to open port 8000.

## Configuration

Edit `.env` (see `.env.example`):

- `SECRET_KEY` — required in any real deployment
- `POSTGRES_PASSWORD` — change the default
- `HTTP_PORT` — host port for the UI (default 3000)
- `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` — set these if you access the UI by hostname or LAN IP

Example LAN access at `http://192.168.0.60:3000`:

```
ALLOWED_HOSTS=*
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://192.168.0.60:3000
```

Then `./scripts/docker-up.sh` again (recreate the backend container so env changes apply).

## LAN discovery

Active scans (ping, ARP, mDNS, SSDP) need to see your LAN.

- **macOS / Windows (Docker Desktop):** multicast and ARP from a bridge network are limited. Use `./scripts/start.sh` on the host if you need full discovery.
- **Linux:** you can try the experimental overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.lan.yml up -d
```

That publishes Postgres/Redis on the host and runs the API on the host network. Prefer it only if you know you need it.

## Troubleshooting

**UI loads but login fails or API 404**

- Confirm health: `curl http://localhost:3000/api/health/`
- Check `docker compose logs frontend` and `docker compose logs backend`

**Backend stays unhealthy**

- First boot runs migrations; wait ~30s
- `docker compose logs backend`

**Need a clean slate**

```bash
./scripts/docker-up.sh --reset
```
