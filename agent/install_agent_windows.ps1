# Duck Monitoring Agent Installation Script for Windows
# Run this script in PowerShell as Administrator

param(
    [string]$ServerUrl = "",
    [string]$Hostname = $env:COMPUTERNAME,
    [string]$InstallDir = "C:\ProgramData\DuckMonitoring",
    [int]$Interval = 60
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Success { param($msg) Write-Host $msg -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host $msg -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host $msg -ForegroundColor Red }

Write-Success "=== Duck Monitoring Agent Installation (Windows) ==="
Write-Host ""

# Validate Server URL
if ([string]::IsNullOrEmpty($ServerUrl) -or $ServerUrl -eq "__SERVER_URL__") {
    Write-Error "Error: Server URL is required"
    Write-Host "Usage: .\install_agent_windows.ps1 -ServerUrl 'http://your-server:8000'"
    exit 1
}

Write-Host "Server URL: $ServerUrl"
Write-Host "Hostname: $Hostname"
Write-Host "Install Directory: $InstallDir"
Write-Host "Collection Interval: $Interval seconds"
Write-Host ""

# Check if Python is installed
Write-Host "Checking for Python..."
$pythonPath = $null
$pythonCommands = @("python", "python3", "py")

foreach ($cmd in $pythonCommands) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match "Python 3") {
            $pythonPath = $cmd
            Write-Success "Found $version"
            break
        }
    } catch {}
}

if (-not $pythonPath) {
    Write-Error "Python 3 is not installed or not in PATH"
    Write-Host "Please install Python 3.8 or higher from https://www.python.org/downloads/"
    Write-Host "Make sure to check 'Add Python to PATH' during installation"
    exit 1
}

# Test server connectivity
Write-Host "Testing server connectivity..."
try {
    $response = Invoke-WebRequest -Uri "$ServerUrl/api/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Success "Server is reachable"
} catch {
    Write-Warning "Warning: Could not reach server at $ServerUrl"
    Write-Host "The agent will retry connecting when started"
}

# Create installation directory
Write-Host "Creating installation directory..."
New-Item -ItemType Directory -Force -Path "$InstallDir\agent" | Out-Null
Set-Location $InstallDir

# Download agent files
Write-Host "Downloading agent files..."
try {
    Invoke-WebRequest -Uri "$ServerUrl/api/agent/files/agent.py" -OutFile "$InstallDir\agent\agent.py" -UseBasicParsing
    Invoke-WebRequest -Uri "$ServerUrl/api/agent/files/requirements.txt" -OutFile "$InstallDir\agent\requirements.txt" -UseBasicParsing
    Write-Success "Agent files downloaded"
} catch {
    Write-Error "Failed to download agent files from server"
    Write-Host "Error: $_"
    exit 1
}

# Create virtual environment
Write-Host "Creating Python virtual environment..."
& $pythonPath -m venv "$InstallDir\venv"

# Install dependencies
Write-Host "Installing dependencies..."
& "$InstallDir\venv\Scripts\pip.exe" install --upgrade pip
& "$InstallDir\venv\Scripts\pip.exe" install -r "$InstallDir\agent\requirements.txt"

# Create configuration file
Write-Host "Creating configuration..."
@"
SERVER_URL=$ServerUrl
HOSTNAME=$Hostname
INTERVAL=$Interval
INSTALL_DIR=$InstallDir
"@ | Out-File -FilePath "$InstallDir\agent_config.env" -Encoding UTF8

# Create start script
Write-Host "Creating start script..."
@"
@echo off
cd /d "$InstallDir"
call venv\Scripts\activate.bat
python agent\agent.py --server "$ServerUrl" --hostname "$Hostname" --interval $Interval
"@ | Out-File -FilePath "$InstallDir\start_agent.bat" -Encoding ASCII

# Create Windows Service using NSSM or Task Scheduler
Write-Host "Setting up Windows Task Scheduler..."

$action = New-ScheduledTaskAction -Execute "$InstallDir\venv\Scripts\python.exe" `
    -Argument "agent\agent.py --server `"$ServerUrl`" --hostname `"$Hostname`" --interval $Interval" `
    -WorkingDirectory $InstallDir

$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

try {
    Unregister-ScheduledTask -TaskName "DuckMonitoringAgent" -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName "DuckMonitoringAgent" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Duck Monitoring Agent"
    Start-ScheduledTask -TaskName "DuckMonitoringAgent"
    Write-Success "Windows Task created and started!"
} catch {
    Write-Warning "Could not create scheduled task (may need Administrator privileges)"
    Write-Host "You can start the agent manually with: $InstallDir\start_agent.bat"
}

Write-Host ""
Write-Success "=== Installation Complete! ==="
Write-Host ""
Write-Host "Agent Configuration:"
Write-Host "  Server URL: $ServerUrl"
Write-Host "  Hostname: $Hostname"
Write-Host "  Install Directory: $InstallDir"
Write-Host "  Collection Interval: $Interval seconds"
Write-Host ""
Write-Host "To start the agent manually:"
Write-Host "  $InstallDir\start_agent.bat"
Write-Host ""
Write-Host "To check task status:"
Write-Host "  Get-ScheduledTask -TaskName 'DuckMonitoringAgent'"
Write-Host ""
Write-Success "The agent should appear in your dashboard shortly!"
