# Duck Monitoring - Hybrid Network Monitoring Tool

A modern, hybrid network monitoring system with agent-based monitoring and historical data visualization.

## Features

- **Agent-based Monitoring**: Lightweight Python agents collect metrics from remote hosts
- **Historical Data Graphing**: Visualize metrics over time with interactive Chart.js charts
- **Real-time Status**: Monitor host health and service status in real-time
- **Service Checks**: CPU, Memory, Disk, and Network monitoring with status indicators
- **SNMP Monitoring**: Monitor HPE iLO and Dell iDRAC devices via SNMP
- **RESTful API**: Clean REST API for managing hosts, checks, and retrieving data
- **Modern Web UI**: React-based dashboard with responsive design and gradient styling
- **Time-series Data**: Store and query historical metrics with flexible time ranges

## Architecture

- **Backend**: Django 6 + Django REST Framework (default port: 8000)
- **Database**: SQLite (local/dev) or PostgreSQL 18 (Docker)
- **Frontend**: React 19 + Vite with Chart.js
- **Agents**: Python-based monitoring agents using psutil

## Project Structure

```
├── backend_django/   # Django API server
│   ├── config/       # Project configuration
│   ├── core/         # Core application logic
│   ├── manage.py     # Django management script
│   └── requirements.txt
├── frontend/         # React web application
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── services/    # API service layer
│   │   └── App.js
│   └── package.json
├── agent/            # Monitoring agent code
│   ├── agent.py      # Main agent script
│   └── requirements.txt
├── scripts/          # Operational scripts
│   ├── start.sh      # Unified startup (setup + Redis + backend + Celery + frontend)
│   ├── stop.sh       # Stop all services
│   ├── status.sh     # Check server status
│   ├── initial_startup.sh  # Alias for start.sh --reset
├── README.md
├── docs/             # Documentation
│   ├── SETUP.md      # Detailed setup instructions
│   ├── QUICKSTART.md # Quick start guide
│   ├── AGENT_INSTALL.md # Agent installation guide
│   └── TROUBLESHOOTING.md # Troubleshooting guide
```

## Quick Start

**Recommended:** Docker Compose (Postgres, Redis, API, Celery, UI):

```bash
./scripts/docker-up.sh
```

Then open `http://localhost:3000` and create the first admin user.

See [docs/DOCKER_QUICKSTART.md](docs/DOCKER_QUICKSTART.md) and [docs/QUICKSTART.md](docs/QUICKSTART.md).

### Using Docker Test Hosts

To quickly test with multiple hosts, use the Docker setup:

```bash
cd docker
./start-hosts.sh
```

This will start 6 test hosts (web servers, database, cache, app servers) that automatically report to your monitoring server. See [docker/README.md](docker/README.md) for details.

## Getting Started

### Start Everything (local/dev)

For host-network discovery on macOS, or working on the code without Docker:

```bash
./scripts/start.sh
```

On first run it automatically:
- Creates the Python virtual environment and installs backend dependencies
- Runs database migrations
- Installs frontend Node dependencies
- Starts Redis if it is not already running
- Starts the Django API (`http://localhost:8000`), Celery worker, and React UI (`http://localhost:3000`)

To wipe the database and start fresh:

```bash
./scripts/start.sh --reset
# or: ./scripts/initial_startup.sh  (same thing)
```

Then open `http://localhost:3000` to register your first admin user.

## Server Management

Docker (recommended):

```bash
./scripts/docker-up.sh
./scripts/docker-down.sh
docker compose logs -f
```

Local/dev:

```bash
./scripts/start.sh    # Start everything (idempotent)
./scripts/stop.sh     # Stop backend, Celery, frontend (and Redis if we started it)
./scripts/status.sh   # Check what's running
```

### Individual Server Control
```bash
./scripts/start-backend.sh   # Start backend only
./scripts/start-frontend.sh  # Start frontend only
```

**Note:** Server logs are written to:
- Backend: `/tmp/duck-monitoring-backend.log`
- Frontend: `/tmp/duck-monitoring-frontend.log`
- Celery: `/tmp/duck-monitoring-celery.log`

### Agent Setup

**One-command installation (recommended):**
```bash
curl -sSL http://your-monitoring-server:8000/api/agent/install.sh | sudo bash
```

**Manual installation:**
```bash
cd agent
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python agent.py --server http://localhost:8000 --hostname my-host
```

## Configuration

Edit `backend_django/config/settings.py` to configure:
- Database connection (default: SQLite - no setup required!)
- API host and port (default: 8000)
- Agent authentication token

### Using PostgreSQL (Optional)

if you want to use PostgreSQL instead of SQLite:
1. Ensure PostgreSQL driver is installed (included in `requirements.txt`)
2. Set `DATABASE_URL` environment variable or edit `config/settings.py`

## API Endpoints

### Hosts
- `GET /api/hosts` - List all hosts
- `GET /api/hosts/<id>` - Get host details
- `POST /api/hosts` - Create a host
- `DELETE /api/hosts/<id>` - Delete a host

### Agent
- `POST /api/agents/register` - Register an agent
- `POST /api/agents/submit` - Submit monitoring data

### Metrics & Checks
- `GET /api/hosts/<id>/metrics` - Get metrics (supports `metric_name`, `metric_type`, `hours` params)
- `GET /api/hosts/<id>/metrics/summary` - Get metrics summary
- `GET /api/hosts/<id>/checks` - Get service checks

## Monitoring Capabilities

### Agent-based Monitoring
The agent monitors:
- **CPU**: Usage percentage, per-core metrics
- **Memory**: Usage, available, total (GB)
- **Disk**: Usage percentage, used/free space for each partition
- **Network**: Bytes sent/received, packets sent/received

### Service Checks (Agentless)
- **Ping**: ICMP connectivity checks
- **SSH**: SSH service availability
- **HTTP/HTTPS**: Web service monitoring
- **TCP/UDP**: Port availability checks
- **DNS**: DNS resolution checks
- **SNMP**: Generic SNMP monitoring with custom OIDs
- **HPE iLO**: SNMP monitoring for HPE Integrated Lights-Out (health, temperature, power, fan status)
- **Dell iDRAC**: SNMP monitoring for Dell Integrated Dell Remote Access Controller (health, temperature, power, fan status)

## Documentation

- [docs/SETUP.md](docs/SETUP.md) - Detailed setup and configuration guide
- [docs/QUICKSTART.md](docs/QUICKSTART.md) - Quick start guide
- [docs/AGENT_INSTALL.md](docs/AGENT_INSTALL.md) - Complete guide for installing agents on remote hosts

## License

This project is open source and available for use.

