# Quick Start Guide

Get up and running with Duck Monitoring in minutes!

## 1. Initial Setup (5 minutes)

```bash
# Navigate to backend
cd backend_django

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run initial setup (creates admin user and configures server)
python manage.py migrate
python reset_admin.py
```

The setup script will guide you through:
- Creating an admin user account
- Setting the server IP address
- Optionally setting a server hostname

## 2. Start Backend Server (1 minute)

```bash
# Make sure you're in the backend directory with venv activated
python manage.py runserver
```

The backend will start on `http://localhost:8000` (or your configured IP)

## 3. Frontend Setup (3 minutes)

In a new terminal:

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start the frontend
npm start
```

The frontend will open at `http://localhost:3000`

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

