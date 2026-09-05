# Troubleshooting

Compose is the supported stack. The UI and the API share **http://localhost:3000**. Health is `GET /api/health/` and returns `{"status":"ok"}`. Hosts live at `/api/inventory/hosts/`, not `/api/hosts`.

## Compose

**UI loads, login fails, or `/api` is 404**

```bash
curl http://localhost:3000/api/health/
docker compose ps
docker compose logs backend
docker compose logs frontend
```

Confirm nginx is proxying: you should not need port 8000 on the host.

**Backend stays unhealthy**

First boot runs migrations. Wait ~30s, then `docker compose logs backend`.

**Changed frontend/backend code, nothing changed in the browser**

Images are baked. Rebuild:

```bash
./scripts/docker-up.sh --rebuild
# or
docker compose up -d --build frontend
docker compose up -d --build backend
```

Hard-refresh the tab.

**CSRF / login from a LAN IP**

Set `CSRF_TRUSTED_ORIGINS` (and `ALLOWED_HOSTS`) in `.env` to include `http://<that-ip>:3000`, then recreate the backend container.

**No MAC, vendor, or names (macOS Docker)**

`./scripts/docker-up.sh` should start `scripts/lan_identity.py` and write `data/lan/identity.json`. If that file is empty or missing, Discovery will look thin. Docker Desktop still cannot do full mDNS; use `./scripts/start.sh` when you need that.

**Watch LAN / checks idle**

```bash
docker compose logs celery-worker
docker compose logs celery-beat
```

**Clean slate**

```bash
./scripts/docker-up.sh --reset
```

## Local `./scripts/start.sh`

Here the API is **http://localhost:8000** and the Vite UI is **http://localhost:3000**.

```bash
curl http://localhost:8000/api/health/
./scripts/status.sh
```

Logs: `/tmp/duck-monitoring-backend.log`, `/tmp/duck-monitoring-frontend.log`, `/tmp/duck-monitoring-celery.log`.

**Backend will not start**

- Port 8000 in use
- `cd backend_django && source venv/bin/activate && python manage.py runserver`
- SQLite at repo-root `db.sqlite3` must be writable

**Frontend will not start**

- Vite, not CRA: `cd frontend && npm start`
- `rm -rf node_modules && npm install` if the lock is confused
- Default API base is `http://<hostname>:8000/api` unless `VITE_API_URL` is set

**Celery / checks idle**

Redis must be running. `./scripts/start.sh` tries to start it.

**Reset local data**

```bash
./scripts/start.sh --reset
```

## Agents

`--server` must be reachable from the agent host.

| How you run the server | Typical `--server` |
|------------------------|--------------------|
| `./scripts/docker-up.sh` | `http://localhost:3000` or `http://<lan-ip>:3000` |
| `./scripts/start.sh` | `http://localhost:8000` |

```bash
# Compose
curl http://localhost:3000/api/health/
# Local
curl http://localhost:8000/api/health/
```

See [AGENT_INSTALL.md](AGENT_INSTALL.md).

## Still stuck

1. Decide which stack you are on (Compose vs `start.sh`) and use the matching health URL.
2. Browser Network tab: 401 is auth; 404 on `/api/hosts` means an old path — use `/api/inventory/hosts/`.
3. Backend tests: `docker compose exec backend python manage.py test` or the same from `backend_django` in a venv.
