#!/usr/bin/env python3
"""
Test host status update with a reachable host (8.8.8.8)
"""
import requests
import json
import sys
import time

API_BASE = "http://localhost:8000/api"

def get_auth_token():
    login_data = {"username": "admin", "password": "admin"}
    try:
        response = requests.post(f"{API_BASE}/auth/token/", json=login_data)
        if response.status_code == 200:
            return response.json().get('access')
    except:
        pass
    return None

def test_reachable_host():
    token = get_auth_token()
    if not token:
        print("Could not get auth token")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Create or get a test host with 8.8.8.8
    print("\n1. Creating/finding test host for 8.8.8.8...")
    response = requests.get(f"{API_BASE}/inventory/hosts/", headers=headers)
    hosts = response.json()
    if isinstance(hosts, dict) and 'results' in hosts:
        hosts = hosts['results']
    
    test_host = None
    for host in hosts:
        if host.get('ip_address') == '8.8.8.8' or host.get('hostname') == 'test-google-dns':
            test_host = host
            break
    
    if not test_host:
        # Create test host
        host_data = {
            "hostname": "test-google-dns",
            "ip_address": "8.8.8.8"
        }
        response = requests.post(f"{API_BASE}/inventory/hosts/", headers=headers, json=host_data)
        if response.status_code in [200, 201]:
            test_host = response.json()
            print(f"   Created host (ID: {test_host['id']})")
        else:
            print(f"   Failed to create host: {response.status_code}")
            return
    else:
        print(f"   Found host (ID: {test_host['id']})")
    
    host_id = test_host['id']
    print(f"   Initial Status: {test_host.get('status', 'N/A')}")
    
    # Get or create ping check
    print("\n2. Getting/creating ping check...")
    response = requests.get(f"{API_BASE}/monitoring/configs/?host={host_id}", headers=headers)
    checks = response.json()
    if isinstance(checks, dict) and 'results' in checks:
        checks = checks['results']
    
    ping_check = None
    for check in checks:
        if check.get('check_type') == 'ping':
            ping_check = check
            break
    
    if not ping_check:
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
            print(f"   Failed to create check: {response.status_code}")
            return
    else:
        print(f"   Found ping check (ID: {ping_check['id']})")
    
    check_id = ping_check['id']
    
    # Run the check
    print(f"\n3. Running ping check on 8.8.8.8...")
    response = requests.post(f"{API_BASE}/monitoring/configs/{check_id}/run/", headers=headers)
    if response.status_code == 200:
        result = response.json()
        check_status = result.get('result', {}).get('status', 'N/A')
        output = result.get('result', {}).get('output', 'N/A')
        print(f"   Check Status: {check_status}")
        print(f"   Output: {output}")
    
    # Wait a moment
    time.sleep(1)
    
    # Check host status
    print("\n4. Checking host status...")
    response = requests.get(f"{API_BASE}/inventory/hosts/{host_id}/", headers=headers)
    if response.status_code == 200:
        updated_host = response.json()
        new_status = updated_host.get('status', 'N/A')
        print(f"   Host Status: {new_status}")
        print(f"   Last Check: {updated_host.get('last_check', 'N/A')}")
        
        if new_status == 'up':
            print(f"\n   ✓ SUCCESS: Host status correctly updated to 'up'")
        elif new_status == 'unknown':
            print(f"\n   ⚠️  WARNING: Host status is still 'unknown'")
            print("   Expected 'up' for successful ping")
        else:
            print(f"\n   Status: {new_status}")

if __name__ == "__main__":
    test_reachable_host()
