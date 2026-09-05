# Agent installation

The agent is optional. Hosts Overview can watch a LAN with ping and Discovery alone. Use an agent when you want CPU, memory, disk, and network from that machine.

Prefer the **Agent** button on Hosts Overview — it builds a command for this server. Manual steps below.

## Which server URL?

| How the server runs | `--server` / curl host |
|---------------------|-------------------------|
| `./scripts/docker-up.sh` | `http://localhost:3000` (or the LAN IP on port 3000). Nginx proxies `/api`. |
| `./scripts/start.sh` | `http://localhost:8000` |

Health: `GET /api/health/` → `{"status":"ok"}`.

## Prerequisites

- Python 3.11+ (3.13 is what CI uses)
- Reachability to the monitoring server
- `pip`, and `curl` or `wget` if you use the one-liner

## Manual install

```bash
cd agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python agent.py --server http://localhost:3000 --hostname my-server-name
```

Use `:8000` if you started the API with `./scripts/start.sh`.

```bash
python agent.py \
  --server http://192.168.0.60:3000 \
  --hostname my-server-name \
  --interval 60
```

Clone the repo or copy only `agent/` onto the target host.

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--server` | Base URL of the monitoring server | required |
| `--hostname` | Name to register | system hostname |
| `--agent-id` | Stable UUID | generated |
| `--auth-token` | Shared token (`AGENT_API_TOKEN` on the server) | none |
| `--interval` | Seconds between posts | 60 |

## Linux (systemd)

```ini
[Unit]
Description=Duck Monitoring Agent
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/opt/duck-monitoring-agent
Environment="PATH=/opt/duck-monitoring-agent/venv/bin"
ExecStart=/opt/duck-monitoring-agent/venv/bin/python agent.py --server http://YOUR-SERVER:3000 --hostname %H
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now duck-monitoring-agent
sudo systemctl status duck-monitoring-agent
```

## macOS (launchd)

`~/Library/LaunchAgents/com.duckmonitoring.agent.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.duckmonitoring.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/duck-monitoring-agent/venv/bin/python</string>
        <string>/opt/duck-monitoring-agent/agent.py</string>
        <string>--server</string>
        <string>http://YOUR-SERVER:3000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/opt/duck-monitoring-agent</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.duckmonitoring.agent.plist
```

There is also `agent/install_agent_macos.sh` if you want a scripted install.

## Windows

NSSM works: point it at `python.exe` with `agent.py --server http://YOUR-SERVER:3000`. `agent/install_agent_windows.ps1` is in the repo.

## Verification

The host should show on Hosts Overview. Open the host detail page for CPU / memory / disk once submit is flowing.

## Troubleshooting

**Cannot connect**

- `--server` host and port match the table above
- `curl http://YOUR-SERVER:3000/api/health/` (or `:8000` locally)
- Firewall allows outbound HTTP

**Never appears**

- Agent stdout / systemd journal
- `docker compose logs backend` or `/tmp/duck-monitoring-backend.log`

**High CPU on the agent host**

Raise `--interval` (default 60s is enough).

## Security

HTTP on a home LAN is the usual setup. For anything exposed further: HTTPS in front of nginx, set `AGENT_API_TOKEN`, and keep the UI off the public internet.

## Uninstall

```bash
sudo systemctl disable --now duck-monitoring-agent
sudo rm /etc/systemd/system/duck-monitoring-agent.service
```

```bash
launchctl unload ~/Library/LaunchAgents/com.duckmonitoring.agent.plist
rm ~/Library/LaunchAgents/com.duckmonitoring.agent.plist
```
