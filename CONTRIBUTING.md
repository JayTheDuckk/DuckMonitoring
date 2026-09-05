# Contributing to Duck Monitoring

Thanks for wanting to change it.

## Issues

Check existing issues first. Open a new one if nothing matches.

## How to run it

Supported path:

```bash
./scripts/docker-up.sh
```

UI: `http://localhost:3000`. After frontend or backend edits, rebuild that image (`./scripts/docker-up.sh --rebuild` or `docker compose up -d --build frontend` / `backend`). Bind-mounts do not include app source.

Local/dev (Vite + Django + SQLite, better LAN multicast):

```bash
./scripts/start.sh
```

Details: [docs/DOCKER_QUICKSTART.md](docs/DOCKER_QUICKSTART.md), [docs/SETUP.md](docs/SETUP.md).

### Backend only

```bash
cd backend_django
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test
```

CI runs these tests on Python 3.13.

### Frontend only

```bash
cd frontend
npm install
npm start    # Vite on port 3000
```

## Pull requests

1. Branch from `main`.
2. Keep the diff focused.
3. If you touch the API or fingerprinting, run the Django tests.
4. Open a **draft** PR early; mark ready when you want review.
5. Do not commit `data/lan/*` (except `.gitkeep`), `frontend/dump.rdb`, or a root `package-lock.json`. Frontend lockfile lives in `frontend/`.

## Style

- Python: PEP 8, Django layout as in `backend_django/`.
- React: existing component folders (`dashboards`, `hosts`, `devices`, `settings`).
- Docs: Docker-first, `/api/inventory/hosts/`, health at `/api/health/`.
