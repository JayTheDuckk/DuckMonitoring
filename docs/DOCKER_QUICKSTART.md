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
4. On macOS, start `scripts/lan_identity.py` so host ARP can be published into `data/lan/identity.json` (mounted into the API)

Open **http://localhost:3000** and complete first-time admin setup.

```bash
./scripts/docker-up.sh --rebuild   # force image rebuild
./scripts/docker-up.sh --reset     # wipe volumes (destroys data)
./scripts/docker-down.sh           # stop, keep data; also stops the host collector
./scripts/docker-down.sh --wipe    # stop and delete volumes
```

Equivalent Compose commands:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f backend
docker compose down
```

Images are baked. After you edit frontend or backend source, rebuild that service (`./scripts/docker-up.sh --rebuild` or `docker compose up -d --build frontend` / `backend`). A refresh alone will not pick up CSS or Python changes.

## What you get

| URL | Purpose |
|---|---|
| http://localhost:3000 | Web UI |
| http://localhost:3000/api/health/ | API health (proxied), `{"status":"ok"}` |
| http://localhost:3000/api/inventory/hosts/ | Host inventory |
| http://localhost:3000/admin/ | Django admin |

The browser talks to the UI only. Nginx proxies `/api`, `/static`, and `/admin` to gunicorn on port 8000 inside the network. You do not publish 8000 on the host.

## Configuration

Edit `.env` (see `.env.example`):

- `SECRET_KEY` — required in any real deployment
- `POSTGRES_PASSWORD` — change the default
- `HTTP_PORT` — host port for the UI (default 3000)
- `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` — set these if you access the UI by hostname or LAN IP
- `AGENT_API_TOKEN` — optional shared token for agents

Example LAN access at `http://192.168.0.60:3000`:

```
ALLOWED_HOSTS=*
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://192.168.0.60:3000
```

Then recreate the backend container so env changes apply (`./scripts/docker-up.sh`).

## LAN discovery

Hosts Overview is a lasting inventory. **Watch LAN** (toggle on that page) keeps adding new observations instead of treating Discovery as a one-shot import.

Active scans (ping, ARP, mDNS, SSDP) need to see your LAN.

- **macOS / Windows (Docker Desktop):** the bridge network cannot do multicast or ARP well. `docker-up.sh` starts a host collector for ARP / MAC / names. For fuller mDNS, use `./scripts/start.sh` on the host.
- **Linux:** you can try the experimental overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.lan.yml up -d
```

That publishes Postgres/Redis on the host and runs the API on the host network. Use it only if you know you need it.

## Troubleshooting

**UI loads but login fails or API 404**

- Confirm health: `curl http://localhost:3000/api/health/`
- `docker compose logs frontend` and `docker compose logs backend`

**Backend stays unhealthy**

- First boot runs migrations; wait ~30s
- `docker compose logs backend`

**Need a clean slate**

```bash
./scripts/docker-up.sh --reset
```
