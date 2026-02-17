# Agent Installation Guide

This guide explains how to install and run the Duck Monitoring agent on a remote host.

## Prerequisites

- Python 3.8 or higher
- Network access to the monitoring server
- `pip` package manager
- `curl` or `wget` (for automatic installation)

## One-Command Installation (Recommended)

The easiest way to install an agent is using the install script served by the API:

```bash
# Download and run the installation script
curl -sSL http://your-monitoring-server:8000/api/agent/install.sh | sudo bash

# Or with custom options
curl -sSL http://your-monitoring-server:8000/api/agent/install.sh | sudo bash -s -- --hostname my-server-name --interval 30
```

**What this does:**
- Downloads the installation script from your monitoring server
- Automatically configures the server URL
- Downloads agent files (agent.py, requirements.txt)
- Creates a Python virtual environment
- Installs dependencies
- Sets up a systemd service (on Linux) for automatic startup
- Starts the agent service

**Options you can pass:**
- `--hostname NAME`: Set a custom hostname (default: system hostname)
- `--install-dir DIR`: Custom installation directory (default: /opt/duck-monitoring-agent)
- `--interval SEC`: Collection interval in seconds (default: 60)

## Manual Installation

If you prefer to install manually:

### Step 1: Copy Agent Files to Target Host

You can either:
- **Option A**: Clone the repository on the target host
- **Option B**: Copy just the `agent/` directory to the target host

```bash
# Option A: Clone repository
git clone <repository-url>
cd "Nagios V2.0/agent"

# Option B: Copy agent directory
scp -r agent/ user@target-host:/opt/duck-monitoring-agent/
ssh user@target-host
cd /opt/duck-monitoring-agent
```

### Step 2: Install Python Dependencies

```bash
cd agent
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Run the Agent

**Basic usage:**
```bash
python agent.py --server http://your-monitoring-server:8000 --hostname my-server-name
```

**With custom options:**
```bash
python agent.py \
  --server http://your-monitoring-server:8000 \
  --hostname my-server-name \
  --interval 60
```

## Running as a Service

### Linux (systemd)

Create a systemd service file for automatic startup:

1. Create the service file:
```bash
sudo nano /etc/systemd/system/duck-monitoring-agent.service
```

2. Add the following content (adjust paths as needed):
```ini
[Unit]
Description=Duck Monitoring Agent
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/opt/duck-monitoring-agent/agent
Environment="PATH=/opt/duck-monitoring-agent/agent/venv/bin"
ExecStart=/opt/duck-monitoring-agent/agent/venv/bin/python agent.py --server http://your-monitoring-server:8000 --hostname %H
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable duck-monitoring-agent
sudo systemctl start duck-monitoring-agent
```

4. Check status:
```bash
sudo systemctl status duck-monitoring-agent
```

### macOS (launchd)

Create a launchd plist file:

1. Create the plist file:
```bash
nano ~/Library/LaunchAgents/com.duckmonitoring.agent.plist
```

2. Add the following content:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.duckmonitoring.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/duck-monitoring-agent/agent/venv/bin/python</string>
        <string>/opt/duck-monitoring-agent/agent/agent.py</string>
        <string>--server</string>
        <string>http://your-monitoring-server:8000</string>
        <string>--hostname</string>
        <string>$(hostname)</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/opt/duck-monitoring-agent/agent</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/duck-monitoring-agent.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/duck-monitoring-agent.error.log</string>
</dict>
</plist>
```

3. Load and start the service:
```bash
launchctl load ~/Library/LaunchAgents/com.duckmonitoring.agent.plist
launchctl start com.duckmonitoring.agent
```

### Windows (Service)

For Windows, you can use NSSM (Non-Sucking Service Manager):

1. Download NSSM from https://nssm.cc/download
2. Install the service:
```cmd
nssm install DuckMonitoringAgent
```

3. Configure the service:
   - **Path**: `C:\Python39\python.exe` (or your Python path)
   - **Startup directory**: `C:\duck-monitoring-agent\agent`
   - **Arguments**: `agent.py --server http://your-monitoring-server:8000 --hostname %COMPUTERNAME%`

4. Start the service:
```cmd
nssm start DuckMonitoringAgent
```

## Agent Options

| Option | Description | Default |
|--------|-------------|---------|
| `--server` | URL of the monitoring server | Required |
| `--hostname` | Hostname to register | System hostname |
| `--agent-id` | Custom agent ID (UUID) | Auto-generated |
| `--auth-token` | Authentication token | None |
| `--interval` | Collection interval in seconds | 60 |

## Example Commands

**Basic installation:**
```bash
python agent.py --server http://192.168.1.100:8000
```

**Custom hostname:**
```bash
python agent.py --server http://192.168.1.100:8000 --hostname web-server-01
```

**Faster collection (30 seconds):**
```bash
python agent.py --server http://192.168.1.100:8000 --interval 30
```

**Remote server:**
```bash
python agent.py --server https://monitoring.example.com:8000 --hostname production-db
```

## Verification

After starting the agent, verify it's working:

1. **Check agent logs** - The agent will print status messages
2. **Check the dashboard** - The host should appear in the Duck Monitoring dashboard
3. **Check metrics** - Navigate to the host detail page to see metrics being collected

## Troubleshooting

### Agent can't connect to server
- Verify the server URL is correct and accessible
- Check firewall rules allow outbound connections
- Test connectivity: `curl http://your-server:8000/api/health`

### Agent not appearing in dashboard
- Check that the agent is running (no errors in output)
- Verify the server is running and accessible
- Check backend logs for registration errors

### Permission errors
- Ensure the agent has permission to read system metrics
- On Linux, may need to run with appropriate permissions
- Check that `psutil` can access system information

### High CPU usage
- Increase the `--interval` to collect less frequently
- Default 60 seconds is usually fine for most use cases

## Security Considerations

- The agent communicates with the server over HTTP by default
- For production, consider:
  - Using HTTPS (configure reverse proxy with SSL)
  - Implementing authentication tokens
  - Using VPN or private network
  - Restricting agent registration to known IPs

## Uninstallation

### Linux (systemd)
```bash
sudo systemctl stop duck-monitoring-agent
sudo systemctl disable duck-monitoring-agent
sudo rm /etc/systemd/system/duck-monitoring-agent.service
sudo systemctl daemon-reload
```

### macOS (launchd)
```bash
launchctl unload ~/Library/LaunchAgents/com.duckmonitoring.agent.plist
rm ~/Library/LaunchAgents/com.duckmonitoring.agent.plist
```

### Windows (NSSM)
```cmd
nssm stop DuckMonitoringAgent
nssm remove DuckMonitoringAgent
```

