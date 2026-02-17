import React, { useState } from 'react';
import './AgentInstall.css';

const AgentInstall = ({ serverUrl, onClose }) => {
  const [hostname, setHostname] = useState('');
  const [interval, setInterval] = useState('60');
  const [installDir, setInstallDir] = useState('/opt/duck-monitoring-agent');
  const [activeTab, setActiveTab] = useState('linux'); // 'linux', 'windows', 'macos', or 'manual'

  // Get the base URL for the API (remove /api suffix if present)
  const getBaseUrl = () => {
    if (serverUrl) {
      return serverUrl.replace(/\/api\/?$/, '');
    }
    // Fallback to current window location
    const protocol = window.location.protocol;
    const host = window.location.hostname;
    const port = window.location.port === '3000' ? '5001' : window.location.port;
    return `${protocol}//${host}${port ? ':' + port : ''}`;
  };

  const baseUrl = getBaseUrl();
  const installScriptUrl = `${baseUrl}/api/agent/install.sh`;

  const handleDownloadScript = () => {
    // Create a download link
    const link = document.createElement('a');
    link.href = installScriptUrl;
    link.download = 'install_agent.sh';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getQuickInstallCommand = () => {
    const params = [];
    if (hostname) params.push(`--hostname ${hostname}`);
    if (interval && interval !== '60') params.push(`--interval ${interval}`);
    if (installDir && installDir !== '/opt/duck-monitoring-agent') params.push(`--install-dir ${installDir}`);

    const paramString = params.length > 0 ? ` -s -- ${params.join(' ')}` : '';
    return `curl -sSL ${installScriptUrl}${paramString} | sudo bash`;
  };

  const getWgetCommand = () => {
    const params = [];
    if (hostname) params.push(`--hostname ${hostname}`);
    if (interval && interval !== '60') params.push(`--interval ${interval}`);
    if (installDir && installDir !== '/opt/duck-monitoring-agent') params.push(`--install-dir ${installDir}`);

    const paramString = params.length > 0 ? ` -- ${params.join(' ')}` : '';
    return `wget -qO- ${installScriptUrl}${paramString} | sudo bash`;
  };

  const copyToClipboard = (text, event) => {
    navigator.clipboard.writeText(text).then(() => {
      // Show a temporary success message
      if (event && event.target) {
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = '✓ Copied!';
        button.style.backgroundColor = '#4caf50';
        setTimeout(() => {
          button.textContent = originalText;
          button.style.backgroundColor = '';
        }, 2000);
      }
    }).catch(err => {
      console.error('Failed to copy:', err);
      alert('Failed to copy to clipboard');
    });
  };

  return (
    <div className="agent-install-overlay" onClick={onClose}>
      <div className="agent-install-modal" onClick={(e) => e.stopPropagation()}>
        <div className="agent-install-header">
          <h2>Install Monitoring Agent</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="agent-install-tabs">
          <button
            className={activeTab === 'linux' ? 'active' : ''}
            onClick={() => { setActiveTab('linux'); setInstallDir('/opt/duck-monitoring-agent'); }}
          >
            Linux
          </button>
          <button
            className={activeTab === 'windows' ? 'active' : ''}
            onClick={() => { setActiveTab('windows'); setInstallDir('C:\\ProgramData\\DuckMonitoring'); }}
          >
            Windows
          </button>
          <button
            className={activeTab === 'macos' ? 'active' : ''}
            onClick={() => { setActiveTab('macos'); setInstallDir('$HOME/.duck-monitoring-agent'); }}
          >
            macOS
          </button>
          <button
            className={activeTab === 'manual' ? 'active' : ''}
            onClick={() => setActiveTab('manual')}
          >
            Manual
          </button>
        </div>

        <div className="agent-install-content">
          <div className="install-options">
            <div className="form-group">
              <label>Hostname (optional):</label>
              <input
                type="text"
                value={hostname}
                onChange={(e) => setHostname(e.target.value)}
                placeholder="Leave empty to use system hostname"
              />
            </div>
            <div className="form-group">
              <label>Interval (seconds):</label>
              <input
                type="number"
                value={interval}
                onChange={(e) => setInterval(e.target.value)}
                min="10"
                max="3600"
              />
            </div>
            <div className="form-group">
              <label>Install Directory:</label>
              <input
                type="text"
                value={installDir}
                onChange={(e) => setInstallDir(e.target.value)}
              />
            </div>
          </div>

          {activeTab === 'linux' && (
            <div className="os-install linux-install">
              <h3>Linux Installation (Bash)</h3>
              <p className="help-text">Run one of these commands on your Linux server:</p>

              <div className="command-box">
                <div className="command-label">Curl</div>
                <code>{`curl -sSL ${baseUrl}/api/agent/install/linux | sudo bash -s -- --server ${baseUrl} --interval ${interval} ${hostname ? `--hostname ${hostname}` : ''}`}</code>
                <button
                  className="copy-button"
                  onClick={(e) => copyToClipboard(`curl -sSL ${baseUrl}/api/agent/install/linux | sudo bash -s -- --server ${baseUrl} --interval ${interval} ${hostname ? `--hostname ${hostname}` : ''}`, e)}
                >
                  Copy
                </button>
              </div>

              <div className="command-box">
                <div className="command-label">Wget</div>
                <code>{`wget -qO- ${baseUrl}/api/agent/install/linux | sudo bash -s -- --server ${baseUrl} --interval ${interval} ${hostname ? `--hostname ${hostname}` : ''}`}</code>
                <button
                  className="copy-button"
                  onClick={(e) => copyToClipboard(`wget -qO- ${baseUrl}/api/agent/install/linux | sudo bash -s -- --server ${baseUrl} --interval ${interval} ${hostname ? `--hostname ${hostname}` : ''}`, e)}
                >
                  Copy
                </button>
              </div>
            </div>
          )}

          {activeTab === 'windows' && (
            <div className="os-install windows-install">
              <h3>Windows Installation (PowerShell)</h3>
              <p className="help-text">Run this command in PowerShell as Administrator:</p>

              <div className="command-box">
                <code>{`Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('${baseUrl}/api/agent/install/windows'))`}</code>
                <button
                  className="copy-button"
                  onClick={(e) => copyToClipboard(`Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('${baseUrl}/api/agent/install/windows'))`, e)}
                >
                  Copy
                </button>
              </div>

              <div className="download-section">
                <p>Or download the installer script:</p>
                <a href={`${baseUrl}/api/agent/install/windows`} className="download-link">
                  Download install_agent_windows.ps1
                </a>
              </div>
            </div>
          )}

          {activeTab === 'macos' && (
            <div className="os-install macos-install">
              <h3>macOS Installation (Bash)</h3>
              <p className="help-text">Run this command on your Mac:</p>

              <div className="command-box">
                <code>{`curl -sSL ${baseUrl}/api/agent/install/macos | bash -s -- --server ${baseUrl} --interval ${interval} ${hostname ? `--hostname ${hostname}` : ''}`}</code>
                <button
                  className="copy-button"
                  onClick={(e) => copyToClipboard(`curl -sSL ${baseUrl}/api/agent/install/macos | bash -s -- --server ${baseUrl} --interval ${interval} ${hostname ? `--hostname ${hostname}` : ''}`, e)}
                >
                  Copy
                </button>
              </div>
            </div>
          )}

          {activeTab === 'manual' && (
            <div className="manual-install">
              <h3>Manual Installation Steps</h3>

              <div className="step">
                <h4>Step 1: Download Agent Files</h4>
                <p>Download the agent files from the server:</p>
                <div className="command-box">
                  <code>curl {baseUrl}/api/agent/files/agent.py -o agent.py</code>
                  <button
                    className="copy-button"
                    onClick={(e) => copyToClipboard(`curl ${baseUrl}/api/agent/files/agent.py -o agent.py`, e)}
                  >
                    Copy
                  </button>
                </div>
                <div className="command-box">
                  <code>curl {baseUrl}/api/agent/files/requirements.txt -o requirements.txt</code>
                  <button
                    className="copy-button"
                    onClick={(e) => copyToClipboard(`curl ${baseUrl}/api/agent/files/requirements.txt -o requirements.txt`, e)}
                  >
                    Copy
                  </button>
                </div>
              </div>

              <div className="step">
                <h4>Step 2: Create Virtual Environment</h4>
                <div className="command-box">
                  <code>python3 -m venv venv</code>
                  <button
                    className="copy-button"
                    onClick={(e) => copyToClipboard('python3 -m venv venv', e)}
                  >
                    Copy
                  </button>
                </div>
                <div className="command-box">
                  <code>source venv/bin/activate</code>
                  <button
                    className="copy-button"
                    onClick={(e) => copyToClipboard('source venv/bin/activate', e)}
                  >
                    Copy
                  </button>
                </div>
              </div>

              <div className="step">
                <h4>Step 3: Install Dependencies</h4>
                <div className="command-box">
                  <code>pip install -r requirements.txt</code>
                  <button
                    className="copy-button"
                    onClick={(e) => copyToClipboard('pip install -r requirements.txt', e)}
                  >
                    Copy
                  </button>
                </div>
              </div>

              <div className="step">
                <h4>Step 4: Run the Agent</h4>
                <div className="command-box">
                  <code>python agent.py --server {baseUrl} {hostname ? `--hostname ${hostname}` : ''} --interval {interval}</code>
                  <button
                    className="copy-button"
                    onClick={(e) => copyToClipboard(`python agent.py --server ${baseUrl} ${hostname ? `--hostname ${hostname}` : ''} --interval ${interval}`, e)}
                  >
                    Copy
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="agent-install-footer">
          <p className="server-info">Server URL: <code>{baseUrl}</code></p>
          <button className="close-button-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};

export default AgentInstall;

