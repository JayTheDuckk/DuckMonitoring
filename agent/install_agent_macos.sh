#!/bin/bash
# Duck Monitoring Agent Installation Script for macOS
# Run with: curl -sSL http://your-server:8000/api/agent/install/macos | bash -s -- --server http://your-server:8000

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Default values
SERVER_URL="${SERVER_URL:-__SERVER_URL__}"
HOSTNAME="${HOSTNAME:-$(hostname)}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.duck-monitoring-agent}"
INTERVAL="${INTERVAL:-60}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server) SERVER_URL="$2"; shift 2 ;;
        --hostname) HOSTNAME="$2"; shift 2 ;;
        --install-dir) INSTALL_DIR="$2"; shift 2 ;;
        --interval) INTERVAL="$2"; shift 2 ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "  --server URL       Monitoring server URL"
            echo "  --hostname NAME    Hostname for this agent"
            echo "  --install-dir DIR  Installation directory (default: ~/.duck-monitoring-agent)"
            echo "  --interval SEC     Collection interval (default: 60)"
            exit 0 ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; exit 1 ;;
    esac
done

echo -e "${GREEN}=== Duck Monitoring Agent Installation (macOS) ===${NC}"
echo ""

# Validate server URL
if [ "$SERVER_URL" = "__SERVER_URL__" ] || [ -z "$SERVER_URL" ]; then
    echo -e "${RED}Error: Server URL is required${NC}"
    echo "Usage: $0 --server http://your-server:8000"
    exit 1
fi

echo "Server URL: $SERVER_URL"
echo "Hostname: $HOSTNAME"
echo "Install Directory: $INSTALL_DIR"
echo "Interval: $INTERVAL seconds"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed${NC}"
    echo "Install with: brew install python3"
    exit 1
fi
echo -e "${GREEN}Found $(python3 --version)${NC}"

# Test server
echo "Testing server connectivity..."
if curl -s --connect-timeout 5 "${SERVER_URL}/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}Server is reachable${NC}"
else
    echo -e "${YELLOW}Warning: Could not reach server${NC}"
fi

# Create directory
echo "Creating installation directory..."
mkdir -p "$INSTALL_DIR/agent"
cd "$INSTALL_DIR"

# Download agent files
echo "Downloading agent files..."
curl -s "${SERVER_URL}/api/agent/files/agent.py" -o agent/agent.py || {
    echo -e "${RED}Failed to download agent.py${NC}"
    exit 1
}
curl -s "${SERVER_URL}/api/agent/files/requirements.txt" -o agent/requirements.txt || {
    echo -e "${RED}Failed to download requirements.txt${NC}"
    exit 1
}
echo -e "${GREEN}Agent files downloaded${NC}"

# Create venv
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r agent/requirements.txt -q

# Create config
cat > agent_config.env <<EOF
SERVER_URL=$SERVER_URL
HOSTNAME=$HOSTNAME
INTERVAL=$INTERVAL
EOF

# Create start script
cat > start_agent.sh <<EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python agent/agent.py --server "$SERVER_URL" --hostname "$HOSTNAME" --interval $INTERVAL
EOF
chmod +x start_agent.sh

# Create LaunchAgent for auto-start (macOS)
PLIST_PATH="$HOME/Library/LaunchAgents/com.duckmonitoring.agent.plist"
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.duckmonitoring.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/venv/bin/python</string>
        <string>$INSTALL_DIR/agent/agent.py</string>
        <string>--server</string>
        <string>$SERVER_URL</string>
        <string>--hostname</string>
        <string>$HOSTNAME</string>
        <string>--interval</string>
        <string>$INTERVAL</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/agent.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/agent.error.log</string>
</dict>
</plist>
EOF

# Load LaunchAgent
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo ""
echo -e "${GREEN}=== Installation Complete! ===${NC}"
echo ""
echo "Agent Configuration:"
echo "  Server URL: $SERVER_URL"
echo "  Hostname: $HOSTNAME"
echo "  Install Directory: $INSTALL_DIR"
echo ""
echo "To check status:"
echo "  launchctl list | grep duckmonitoring"
echo ""
echo "To view logs:"
echo "  tail -f $INSTALL_DIR/agent.log"
echo ""
echo "To stop:"
echo "  launchctl unload $PLIST_PATH"
echo ""
echo -e "${GREEN}The agent should appear in your dashboard shortly!${NC}"
