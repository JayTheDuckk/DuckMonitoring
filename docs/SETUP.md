# Local / dev setup

The supported run path is Docker Compose: [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) and `./scripts/docker-up.sh`.

Use this page when you want a host-network stack (venv + Vite + SQLite) for editing code or for Discovery on Docker Desktop.

## Prerequisites

- Python 3.13 preferred (3.11+ usually works). CI and the backend image use 3.13.
- Node.js 22 and npm (the frontend image uses Node 22)
- Redis (for Celery). `./scripts/start.sh` starts it if it can.

## Start everything

From the repo root:

```bash
./scripts/start.sh
```

That creates the backend venv, installs dependencies, migrates SQLite (`db.sqlite3` at the repo root), installs frontend packages, starts Redis if needed, then:

- Django API on `http://localhost:8000`
- Vite UI on `http://localhost:3000` (talks to the API on 8000 unless `VITE_API_URL` is set)
- Celery worker

```bash
./scripts/stop.sh
./scripts/status.sh
./scripts/start.sh --reset    # wipe SQLite and start fresh
```

Open **http://localhost:3000** and create the first admin user.

Logs: `/tmp/duck-monitoring-backend.log`, `/tmp/duck-monitoring-frontend.log`, `/tmp/duck-monitoring-celery.log`.

### One service at a time

```bash
./scripts/start-backend.sh
./scripts/start-frontend.sh
```

Frontend is Vite (`npm start` / `npm run dev`), not Create React App.

## Database

Local `start.sh` uses SQLite. Compose uses Postgres 18 via `DATABASE_URL`.

To point a local backend at Postgres:

```
DATABASE_URL=postgres://duck:change-me@localhost:5432/duck_monitoring
```

## Agent (local stack)

```bash
cd agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python agent.py --server http://localhost:8000 --hostname my-server
```

| Option | Meaning | Default |
|--------|---------|---------|
| `--server` | API base URL the agent can reach | required |
| `--hostname` | Name to register | system hostname |
| `--agent-id` | Stable UUID | generated |
| `--auth-token` | Shared token (`AGENT_API_TOKEN`) | none |
| `--interval` | Seconds between posts | 60 |

Against Compose, use `--server http://localhost:3000` instead. Full notes: [AGENT_INSTALL.md](AGENT_INSTALL.md).

## Useful API paths

These are on the API host (`:8000` locally, or `:3000/api` through nginx in Compose):

| Path | Purpose |
|------|---------|
| `/api/health/` | Liveness, `{"status":"ok"}` |
| `/api/auth/token/` | JWT login |
| `/api/inventory/hosts/` | Lasting host inventory |
| `/api/inventory/groups/` | Host groups |
| `/api/inventory/watch/` | Watch LAN setting |
| `/api/discovery/` | Scan jobs and results |
| `/api/agents/register/` | Agent registration |
| `/api/agents/submit/` | Agent metrics |
| `/api/alerts/` | Rules and channels |
| `/api/monitoring/` | Checks, configs, metrics |
| `/api/topology/graph` | Topology |

There is no `/api/hosts` — that moved under inventory.

## Troubleshooting

**Backend will not start**

- Port 8000 in use
- Venv missing deps: `backend_django/venv` and `pip install -r requirements.txt`
- SQLite file not writable at repo-root `db.sqlite3`

**Frontend will not talk to the API**

- API health: `curl http://localhost:8000/api/health/`
- Vite defaults to `http://<hostname>:8000/api` when `VITE_API_URL` is unset
- Browser console for CORS / 401

**Celery idle**

- Redis must be up. `./scripts/start.sh` tries to start it.
- `/tmp/duck-monitoring-celery.log`
