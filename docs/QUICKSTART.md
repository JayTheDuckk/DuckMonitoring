# Quick Start Guide

Get up and running with Duck Monitoring in minutes!

## 1. Start the Application (5 minutes)

Duck Monitoring comes with a streamlined initial startup script that automatically creates the database, installs dependencies, and starts the frontend and backend servers.

```bash
# From the project root, run the initial setup script
./scripts/initial_startup.sh
```

**Note:** This script is intended for first-time installation and will prompt you to confirm resetting the database.

The script will:
- Create a Python virtual environment
- Install backend dependencies
- Run initial database migrations
- Install frontend dependencies
- Start the API on `http://localhost:8000`
- Start the Web UI on `http://localhost:3000`

## 2. Initial Browser Setup (1 minute)

Once the script finishes starting the servers:
1. Open your browser to `http://localhost:3000`
2. You will be automatically redirected to the **Setup** page
3. Create your first administrative user account

## 3. Regular Restarts

For regular use (after the initial setup), you can simply use the standard start and stop scripts:
```bash
./scripts/start.sh
./scripts/stop.sh
```

## 4. Start an Agent (2 minutes)

In another terminal:

```bash
# Navigate to agent
cd agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the agent
python agent.py --server http://localhost:8000
```

This will start 6 test hosts (web servers, database, cache, app servers) that automatically report to your monitoring server. See [../docker/README.md](../docker/README.md) for details.

## 5. View Your Dashboard

Open your browser to `http://localhost:3000` and you should see:
- Your host registered in the dashboard
- Real-time status updates
- Service checks (CPU, Memory, Disk)
- Historical metrics ready to graph

## Next Steps

- Add more agents on different machines
- Explore the host detail pages to view graphs
- Customize the monitoring interval with `--interval` flag
- Configure PostgreSQL for production use

## Troubleshooting

**Backend won't start:**
- Check if port 8000 is available
- If port 8000 is in use, check `manage.py runserver` options
- Verify Python 3.8+ is installed
- Ensure all dependencies are installed

**Frontend won't connect:**
- Verify backend is running on port 8000 (or your custom port)
- Check browser console for errors
- Ensure CORS is enabled (it is by default)

**Agent won't register:**
- Verify backend URL is correct
- Check network connectivity
- Ensure backend is running

