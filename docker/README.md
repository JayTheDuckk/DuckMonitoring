# Docker test hosts

Fake agents that report into a running Duck Monitoring server. They are not the main stack — that is `./scripts/docker-up.sh` at the repo root.

## Point them at the right API

| Server you already started | `SERVER_URL` |
|----------------------------|--------------|
| `./scripts/start.sh` (API on host :8000) | `http://host.docker.internal:8000` (default in this compose file) |
| `./scripts/docker-up.sh` (UI/API on host :3000) | `http://host.docker.internal:3000` |

Health check from your Mac:

```bash
# local start.sh
curl http://localhost:8000/api/health/
# Compose
curl http://localhost:3000/api/health/
```

On Linux, `host.docker.internal` may need the host IP instead.

## Start

```bash
cd docker
docker compose up -d
```

The compose file defaults to `:8000`. For the main Compose stack, change each service’s `SERVER_URL` to `http://host.docker.internal:3000`, then `docker compose up -d --build`.

```bash
docker compose ps
docker compose logs -f
docker compose logs -f web-server-1
docker compose down
```

## Hosts

- web-server-1 / web-server-2
- db-server
- cache-server
- app-server-1 / app-server-2

Each runs the monitoring agent about every 30 seconds (`INTERVAL`). They should show up on Hosts Overview.

## Tweaks

- **Interval:** `CMD` / `INTERVAL` in `Dockerfile.agent` or the service environment.
- **More hosts:** copy a service block; change `container_name`, `HOSTNAME`, and `AGENT_ID`.

## Troubleshooting

**Not connecting**

- Server health URL from the table above
- `host.docker.internal` works on Docker Desktop; on Linux use the host IP
- `docker compose logs web-server-1`

**Rebuild**

```bash
docker compose build
docker compose up -d
```
