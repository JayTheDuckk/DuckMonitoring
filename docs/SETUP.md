# Setup Instructions

## Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher and npm
- PostgreSQL (optional, SQLite is used by default)

## Initial Setup

Run the unified startup script from the project root:

```bash
./scripts/start.sh
```

This handles everything automatically — virtual environment, dependencies, migrations, Redis, backend, Celery, and frontend.

To factory-reset (wipes the SQLite database):

```bash
./scripts/start.sh --reset
```

Then open `http://localhost:3000` to register your first admin user.

## Database Configuration (Optional)

- Default uses SQLite (`db.sqlite3`) - no additional setup needed!
- For PostgreSQL: 
  - Ensure PostgreSQL driver is installed (included in `requirements.txt`)
  - Edit `config/settings.py` or set environment variable: `DATABASE_URL=postgresql://user:password@localhost/duck_monitoring`

## Agent Setup

1. Navigate to the agent directory:
```bash
cd agent
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the agent:
```bash
python agent.py --server http://localhost:8000 --hostname my-server
```

### Agent Options

- `--server`: URL of the monitoring server (required)
- `--hostname`: Hostname to register (default: system hostname)
- `--agent-id`: Custom agent ID (default: auto-generated UUID)
- `--auth-token`: Authentication token (if configured)
- `--interval`: Collection interval in seconds (default: 60)

## Running the Complete System

1. Start the backend server (Terminal 1):
```bash
cd backend_django
python manage.py runserver
```

2. Start the frontend (Terminal 2):
```bash
cd frontend
npm start
```

3. Start one or more agents (Terminal 3+):
```bash
cd agent
python agent.py --server http://localhost:8000
```

## API Endpoints

### Hosts
- `GET /api/hosts` - List all hosts
- `GET /api/hosts/<id>` - Get host details
- `POST /api/hosts` - Create a host
- `DELETE /api/hosts/<id>` - Delete a host

### Agent
- `POST /api/agents/register` - Register an agent
- `POST /api/agents/submit` - Submit monitoring data

### Metrics
- `GET /api/hosts/<id>/metrics` - Get metrics for a host
- `GET /api/hosts/<id>/metrics/summary` - Get metrics summary
- `GET /api/hosts/<id>/checks` - Get service checks for a host

## Troubleshooting

### Backend Issues
- Ensure all dependencies are installed
- Check that the database file is writable (for SQLite)
- Verify the port 8000 is not in use

### Frontend Issues
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check that the backend is running and accessible
- Verify CORS is enabled in the backend

### Agent Issues
- Verify the server URL is correct and accessible
- Check network connectivity
- Ensure psutil is installed correctly

