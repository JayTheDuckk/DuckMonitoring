# Quick Start Guide

Get up and running with Duck Monitoring in minutes!

## 1. Start Everything

One script does it all — setup, Redis, backend, Celery, and frontend:

```bash
./scripts/start.sh
```

On first run it will automatically:
- Create a Python virtual environment and install backend dependencies
- Run database migrations
- Install frontend Node dependencies
- Start Redis if it is not already running
- Start the API on `http://localhost:8000`
- Start the Web UI on `http://localhost:3000`

## 2. Initial Browser Setup

Once the script finishes:
1. Open your browser to `http://localhost:3000`
2. You will be redirected to the **Setup** page
3. Create your first administrative user account

## 3. Daily Use

```bash
./scripts/start.sh    # Start everything
./scripts/stop.sh     # Stop everything
./scripts/status.sh   # Check what's running
```

To wipe the database and start fresh:

```bash
./scripts/start.sh --reset
```

## 4. Start an Agent

In another terminal:

```bash
cd agent
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python agent.py --server http://localhost:8000
```

Or use Docker test hosts — see [../docker/README.md](../docker/README.md).

## 5. View Your Dashboard

Open `http://localhost:3000` to see:
- Registered hosts and real-time status
- Service checks (CPU, Memory, Disk)
- Historical metrics and graphs

## Troubleshooting

**Backend won't start:**
- Check if port 8000 is available
- Verify Python 3.8+ is installed

**Service checks not running:**
- Redis must be running for Celery — `./scripts/start.sh` starts it automatically if possible
- Check Celery logs: `/tmp/duck-monitoring-celery.log`

**Frontend won't connect:**
- Verify backend is running: `curl http://localhost:8000/api/health/`
- Check browser console for errors

**Agent won't register:**
- Verify backend URL is correct
- Ensure backend is running
