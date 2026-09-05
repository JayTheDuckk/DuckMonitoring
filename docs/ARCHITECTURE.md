# Architecture

Duck Monitoring is a personal LAN inventory and monitoring stack. The browser talks to one origin. Agents and agentless polls are optional.

## Compose topology (supported)

```text
                         Host LAN collector (macOS)
                         scripts/lan_identity.py
                         data/lan/identity.json
                                    |
+------------------+                v
| Browser :3000    |     +----------------------+
| Hosts, Discovery |     | frontend (nginx)     |
| Alerts, Hardware |---->| SPA + /api /admin    |
+------------------+     +----------+-----------+
                                    |
                                    v
                         +----------------------+      +--------+
                         | backend (gunicorn)   |<---->| Redis  |
                         | Django 6 + DRF       |      +--------+
                         | inventory, discovery |           |
                         | alerts, agents       |      +----+-----+
                         +----------+-----------+      | Celery   |
                                    |                  | worker + |
                                    v                  | beat     |
                         +----------------------+      +----------+
                         | Postgres 18          |
                         +----------------------+

Optional: Python agents POST /api/agents/submit/
Optional: Watch LAN + Celery ping / SNMP / UPS
```

You do not publish port 8000. Nginx in the UI container proxies `/api` and `/admin` to gunicorn.

Local `./scripts/start.sh` is the same apps without Compose: Vite on 3000, Django on 8000, SQLite, host-network Discovery.

## Pieces

### Frontend

React 19 + Vite SPA. Production image is a static nginx build (`VITE_API_URL=/api`).

- Routing: `react-router-dom`
- Auth: JWT in `localStorage`, Axios interceptor on `frontend/src/services/api.js`
- Theme: IBM Plex Mono, light/dark tokens in `frontend/src/index.css`

Hosts Overview is the lasting inventory (groups, drag-and-drop, Watch LAN). Discovery is the scan/import surface.

### Backend

Django 6 + Django REST Framework. Apps:

| App | Role |
|-----|------|
| `accounts` | Users, first-run setup, audit log |
| `inventory` | Hosts, groups, UPS, SNMP, Watch LAN |
| `discovery` | Scan jobs, observations, persistence |
| `monitoring` | Agent ingest, checks, metrics, dashboards |
| `alerts` | Rules, channels, default new/gone/down pack |
| `topology` | Graph for the map page |
| `core` | Fingerprint, mDNS, quiet probe, SNMP/UPS helpers |

OS labels are only stored when fingerprinting can name a specific OS (Windows, macOS, iOS, tvOS, Android, Linux, Embedded Linux). Slash-unions like “iOS/Android/macOS” are not shown.

### Data

- **Compose:** Postgres. Host identity from the macOS collector is a JSON file under `data/lan/` (gitignored).
- **Local start.sh:** SQLite at repo-root `db.sqlite3`.
- Metrics are relational rows. Redis is the Celery broker.

### Agents

Lightweight `psutil` loop. If the server is down, the current payload is dropped. Register/submit live at `/api/agents/register/` and `/api/agents/submit/`. Optional `AGENT_API_TOKEN`.

### Agentless / LAN

Celery runs ping and other service checks. Discovery combines active scan with passive mDNS, SSDP, and ARP. Watch LAN writes new observations into `Host` rows so the Overview does not reset on every scan.

## Security

- Browser users get JWT access + refresh tokens.
- First admin is created in the setup wizard; there is no fixture password.
- Agents use a generated UUID and optional shared token.
- Admin actions write `AuditLog` rows (Settings → Audit log).

## Rebuild note

Frontend and backend images copy source at build time. After you change CSS, JS, or Python, rebuild that service. Bind-mounts are only used for `data/lan`.
