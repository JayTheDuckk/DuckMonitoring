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

- **Backend**: Django REST Framework (default port: 8000)
- **Database**: SQLite (default) or PostgreSQL (optional)
- **Frontend**: React with Chart.js for visualizations
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
│   ├── start.sh      # Start both servers
│   ├── stop.sh       # Stop both servers
│   ├── status.sh     # Check server status
│   ├── start-backend.sh  # Start backend only
│   └── start-frontend.sh # Start frontend only
├── README.md
├── docs/             # Documentation
│   ├── SETUP.md      # Detailed setup instructions
│   ├── QUICKSTART.md # Quick start guide
│   ├── AGENT_INSTALL.md # Agent installation guide
│   └── TROUBLESHOOTING.md # Troubleshooting guide
```

## Quick Start

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for a step-by-step guide to get running in minutes.

### Using Docker Test Hosts

To quickly test with multiple hosts, use the Docker setup:

```bash
cd docker
./start-hosts.sh
```

This will start 6 test hosts (web servers, database, cache, app servers) that automatically report to your monitoring server. See [docker/README.md](docker/README.md) for details.

## Getting Started

## Getting Started

## Getting Started

### Initial Setup

Duck Monitoring handles its own bootstrapping automatically using the provided initial setup script. You do not need to manually create virtual environments or install dependencies.

1. **Start Initial Setup:**
   From the project root directory, run the setup script:
   ```bash
   ./scripts/initial_startup.sh
   ```
   
   **Warning:** This script is intended for first-time installation and will ask you to confirm a database reset.
   
   The script will:
   - Create a Python virtual environment
   - Install backend requirements and run fresh database migrations
   - Install frontend Node dependencies
   - Start both the Django API (`http://localhost:8000`) and the React UI (`http://localhost:3000`)

2. **Register Admin User:**
   Once the servers are running, open your web browser to `http://localhost:3000`. You will be directed to an **Initial Setup** page to create your first administrative user.

## Server Management

Easy-to-use scripts for subsequent starts and stops:

### Start Both Servers
```bash
./scripts/start.sh
```
Starts both backend and frontend servers in the background (requires `initial_startup.sh` to have been run at least once).

### Stop Both Servers
```bash
./scripts/stop.sh
```
Stops both backend and frontend servers.

### Check Server Status
```bash
./scripts/status.sh
```
Shows which servers are currently running.

### Individual Server Control
```bash
./scripts/start-backend.sh   # Start backend only
./scripts/start-frontend.sh  # Start frontend only
```

**Note:** Server logs are written to:
- Backend: `/tmp/duck-monitoring-backend.log`
- Frontend: `/tmp/duck-monitoring-frontend.log`

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

