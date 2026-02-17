#!/usr/bin/env python3
"""
Test that host status is updated when service checks run
"""
import requests
import json
import sys
import time

API_BASE = "http://localhost:8000/api"

def get_auth_token():
    """Get authentication token"""
    login_data = {
        "username": "admin",
        "password": "admin"
    }
    
    try:
        response = requests.post(f"{API_BASE}/auth/token/", json=login_data)
        if response.status_code == 200:
            return response.json().get('access')
        else:
            print(f"Login failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting token: {e}")
        return None

def test_host_status_update():
    """Test that host status updates when ping check runs"""
    token = get_auth_token()
    if not token:
        print("Could not get auth token")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Get hosts
    print("\n1. Getting hosts...")
    response = requests.get(f"{API_BASE}/inventory/hosts/", headers=headers)
    if response.status_code != 200:
        print(f"Failed to get hosts: {response.status_code}")
        return
    
    hosts = response.json()
    if isinstance(hosts, dict) and 'results' in hosts:
        hosts = hosts['results']
    elif not isinstance(hosts, list):
        hosts = []
    
    if len(hosts) == 0:
        print("No hosts found")
        return
    
    # Use first host
    host = hosts[0]
    host_id = host['id']
    print(f"   Host: {host.get('hostname', 'N/A')} (ID: {host_id})")
    print(f"   Current Status: {host.get('status', 'N/A')}")
    
    # Get or create ping check
    print("\n2. Getting ping service check...")
    response = requests.get(f"{API_BASE}/monitoring/configs/?host={host_id}", headers=headers)
    if response.status_code != 200:
        print(f"Failed to get checks: {response.status_code}")
        return
    
    checks = response.json()
    if isinstance(checks, dict) and 'results' in checks:
        checks = checks['results']
    elif not isinstance(checks, list):
        checks = []
    
    ping_check = None
    for check in checks:
        if check.get('check_type') == 'ping':
            ping_check = check
            break
    
    if not ping_check:
        print("   No ping check found, creating one...")
        check_data = {
            "host": host_id,
            "check_type": "ping",
            "check_name": "Ping Check",
            "enabled": True,
            "interval": 60,
            "timeout": 10,
            "parameters": {"count": 3}
        }
        response = requests.post(f"{API_BASE}/monitoring/configs/", headers=headers, json=check_data)
        if response.status_code in [200, 201]:
            ping_check = response.json()
            print(f"   Created ping check (ID: {ping_check['id']})")
        else:
            print(f"   Failed to create: {response.status_code}")
            return
    else:
        print(f"   Found ping check (ID: {ping_check['id']})")
    
    check_id = ping_check['id']
    
    # Run the check
    print(f"\n3. Running ping check (ID: {check_id})...")
    response = requests.post(f"{API_BASE}/monitoring/configs/{check_id}/run/", headers=headers)
    print(f"   Response: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Check Status: {result.get('result', {}).get('status', 'N/A')}")
        print(f"   Output: {result.get('result', {}).get('output', 'N/A')}")
    
    # Wait a moment
    time.sleep(1)
    
    # Check host status
    print("\n4. Checking host status after ping check...")
    response = requests.get(f"{API_BASE}/inventory/hosts/{host_id}/", headers=headers)
    if response.status_code == 200:
        updated_host = response.json()
        new_status = updated_host.get('status', 'N/A')
        print(f"   Host Status: {new_status}")
        print(f"   Last Check: {updated_host.get('last_check', 'N/A')}")
        
        if new_status != 'unknown':
            print(f"\n   ✓ SUCCESS: Host status updated to '{new_status}'")
        else:
            print(f"\n   ⚠️  WARNING: Host status is still 'unknown'")
            print("   The host status update logic may not be working correctly")
    else:
        print(f"   Failed to get host: {response.status_code}")

if __name__ == "__main__":
    test_host_status_update()
