#!/usr/bin/env python3
"""
Duck Monitoring Agent
Collects system metrics and sends them to the monitoring server
"""

import argparse
import time
import socket
import uuid
import psutil
import requests
from datetime import datetime

class MonitoringAgent:
    def __init__(self, server_url, hostname=None, agent_id=None, auth_token=None, interval=60):
        self.server_url = server_url.rstrip('/')
        self.hostname = hostname or socket.gethostname()
        self.agent_id = agent_id or str(uuid.uuid4())
        self.auth_token = auth_token
        self.interval = interval
        self.running = False
        
    def get_ip_address(self):
        """Get the primary IP address of the host"""
        try:
            # Connect to a remote address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def collect_checks(self):
        """Collect service checks"""
        checks = []
        
        # CPU check
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_status = 'ok' if cpu_percent < 80 else 'warning' if cpu_percent < 95 else 'critical'
        checks.append({
            'type': 'cpu',
            'name': 'CPU Usage',
            'status': cpu_status,
            'output': f'CPU usage is {cpu_percent:.1f}%'
        })
        
        # Memory check
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_status = 'ok' if memory_percent < 80 else 'warning' if memory_percent < 95 else 'critical'
        checks.append({
            'type': 'memory',
            'name': 'Memory Usage',
            'status': memory_status,
            'output': f'Memory usage is {memory_percent:.1f}% ({memory.used / (1024**3):.2f} GB / {memory.total / (1024**3):.2f} GB)'
        })
        
        # Disk checks
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_percent = usage.percent
                disk_status = 'ok' if disk_percent < 80 else 'warning' if disk_percent < 95 else 'critical'
                checks.append({
                    'type': 'disk',
                    'name': f'Disk {partition.mountpoint}',
                    'status': disk_status,
                    'output': f'Disk {partition.mountpoint} usage is {disk_percent:.1f}% ({usage.used / (1024**3):.2f} GB / {usage.total / (1024**3):.2f} GB)'
                })
            except PermissionError:
                pass
        
        return checks
    
    def collect_metrics(self):
        """Collect time-series metrics"""
        metrics = []
        timestamp = datetime.utcnow()
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics.append({
            'name': 'cpu.usage',
            'type': 'cpu',
            'value': cpu_percent,
            'unit': '%'
        })
        
        # Per-core CPU metrics
        cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
        for i, core_percent in enumerate(cpu_per_core):
            metrics.append({
                'name': f'cpu.core.{i}',
                'type': 'cpu',
                'value': core_percent,
                'unit': '%'
            })
        
        # Memory metrics
        memory = psutil.virtual_memory()
        metrics.append({
            'name': 'memory.usage',
            'type': 'memory',
            'value': memory.percent,
            'unit': '%'
        })
        metrics.append({
            'name': 'memory.used',
            'type': 'memory',
            'value': memory.used / (1024**3),  # Convert to GB
            'unit': 'GB'
        })
        metrics.append({
            'name': 'memory.available',
            'type': 'memory',
            'value': memory.available / (1024**3),  # Convert to GB
            'unit': 'GB'
        })
        metrics.append({
            'name': 'memory.total',
            'type': 'memory',
            'value': memory.total / (1024**3),  # Convert to GB
            'unit': 'GB'
        })
        
        # Disk metrics
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                metrics.append({
                    'name': f'disk.{partition.mountpoint.replace("/", "_")}.usage',
                    'type': 'disk',
                    'value': usage.percent,
                    'unit': '%'
                })
                metrics.append({
                    'name': f'disk.{partition.mountpoint.replace("/", "_")}.used',
                    'type': 'disk',
                    'value': usage.used / (1024**3),  # Convert to GB
                    'unit': 'GB'
                })
                metrics.append({
                    'name': f'disk.{partition.mountpoint.replace("/", "_")}.free',
                    'type': 'disk',
                    'value': usage.free / (1024**3),  # Convert to GB
                    'unit': 'GB'
                })
            except PermissionError:
                pass
        
        # Network metrics
        net_io = psutil.net_io_counters()
        metrics.append({
            'name': 'network.bytes_sent',
            'type': 'network',
            'value': net_io.bytes_sent / (1024**2),  # Convert to MB
            'unit': 'MB'
        })
        metrics.append({
            'name': 'network.bytes_recv',
            'type': 'network',
            'value': net_io.bytes_recv / (1024**2),  # Convert to MB
            'unit': 'MB'
        })
        metrics.append({
            'name': 'network.packets_sent',
            'type': 'network',
            'value': net_io.packets_sent,
            'unit': 'packets'
        })
        metrics.append({
            'name': 'network.packets_recv',
            'type': 'network',
            'value': net_io.packets_recv,
            'unit': 'packets'
        })
        
        return metrics
    
    def register(self):
        """Register this agent with the server"""
        try:
            response = requests.post(
                f'{self.server_url}/api/agents/register',
                json={
                    'agent_id': self.agent_id,
                    'hostname': self.hostname,
                    'ip_address': self.get_ip_address()
                },
                headers={'Authorization': f'Bearer {self.auth_token}'} if self.auth_token else None,
                timeout=10
            )
            if response.status_code == 200:
                print(f"Agent registered successfully: {self.agent_id}")
                return True
            else:
                print(f"Registration failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Registration error: {e}")
            return False
    
    def submit_data(self):
        """Collect and submit monitoring data"""
        try:
            checks = self.collect_checks()
            metrics = self.collect_metrics()
            
            payload = {
                'agent_id': self.agent_id,
                'checks': checks,
                'metrics': metrics
            }
            
            response = requests.post(
                f'{self.server_url}/api/agents/submit',
                json=payload,
                headers={'Authorization': f'Bearer {self.auth_token}'} if self.auth_token else None,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"[{datetime.now()}] Data submitted successfully")
                return True
            else:
                print(f"[{datetime.now()}] Submission failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[{datetime.now()}] Submission error: {e}")
            return False
    
    def run(self):
        """Main agent loop"""
        print(f"Starting monitoring agent: {self.agent_id}")
        print(f"Server: {self.server_url}")
        print(f"Hostname: {self.hostname}")
        print(f"Interval: {self.interval} seconds")
        
        # Register agent
        if not self.register():
            print("Failed to register agent. Exiting.")
            return
        
        # Main monitoring loop
        self.running = True
        while self.running:
            self.submit_data()
            time.sleep(self.interval)
    
    def stop(self):
        """Stop the agent"""
        self.running = False

def main():
    parser = argparse.ArgumentParser(description='Duck Monitoring Agent')
    parser.add_argument('--server', required=True, help='Monitoring server URL (e.g., http://localhost:8000)')
    parser.add_argument('--hostname', help='Hostname (default: system hostname)')
    parser.add_argument('--agent-id', help='Agent ID (default: auto-generated UUID)')
    parser.add_argument('--auth-token', help='Authentication token')
    parser.add_argument('--interval', type=int, default=60, help='Collection interval in seconds (default: 60)')
    
    args = parser.parse_args()
    
    agent = MonitoringAgent(
        server_url=args.server,
        hostname=args.hostname,
        agent_id=args.agent_id,
        auth_token=args.auth_token,
        interval=args.interval
    )
    
    try:
        agent.run()
    except KeyboardInterrupt:
        print("\nStopping agent...")
        agent.stop()

if __name__ == '__main__':
    main()

