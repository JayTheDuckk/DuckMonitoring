# Quick Start

Docker Compose is the supported path. The UI is `http://localhost:3000`; nginx proxies `/api` and `/admin`.

## 1. Start the stack

```bash
./scripts/docker-up.sh
```

That creates `.env` if needed, starts Postgres, Redis, the API, Celery, and the UI, and on macOS starts a host collector so ARP / MAC / names can still reach Docker.

Open **http://localhost:3000** and create the first admin user.

More Compose detail: [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md).

## 2. First hour in the UI

1. **Hosts Overview** (`/`) — lasting inventory. Add a group, add a host, or turn on **Watch LAN** so new devices are kept automatically.
2. **Discovery** (`/discovery`) — scan a subnet, then import what you want (or let Watch LAN do it).
3. **Alerts** — a default pack covers new, gone, and down hosts. Add a channel if you want notifications.
4. **Hardware** — UPS and SNMP if you have them.
5. **Agent** — optional. Use the Agent button on Hosts Overview, or see [AGENT_INSTALL.md](AGENT_INSTALL.md).

## 3. Daily commands

```bash
./scripts/docker-up.sh
./scripts/docker-down.sh
docker compose logs -f
```

Rebuild after frontend or backend edits (`./scripts/docker-up.sh --rebuild`). Wipe volumes with `./scripts/docker-up.sh --reset`.

## 4. Local / dev (no Compose)

Use this to edit against a host-network stack, or when Docker Desktop cannot see multicast:

```bash
./scripts/start.sh            # API :8000, Vite UI :3000, Redis, Celery
./scripts/stop.sh
./scripts/status.sh
./scripts/start.sh --reset    # wipe the local SQLite database
```

Health is then `http://localhost:8000/api/health/`. Agents should use `--server http://localhost:8000`.

## 5. Optional agent

Against Compose:

```bash
cd agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python agent.py --server http://localhost:3000 --hostname my-host
```

Fake lab agents: [../docker/README.md](../docker/README.md).

## Troubleshooting

**UI loads, API 404 or login fails**

```bash
curl http://localhost:3000/api/health/
docker compose logs backend
docker compose logs frontend
```

**Checks never run**

Celery needs Redis. `docker compose logs celery-worker` (Compose) or `/tmp/duck-monitoring-celery.log` (local).

**No MAC / vendor / names on macOS Docker**

Confirm `./scripts/docker-up.sh` started the host collector (`data/lan/identity.json`). Full mDNS from Docker Desktop is still limited; `./scripts/start.sh` sees more.

**Agent will not register**

`--server` must be the URL the agent can reach. Compose: port **3000**. Local `start.sh`: port **8000**.
