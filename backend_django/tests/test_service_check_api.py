#!/usr/bin/env python3
"""
Test service check via API
"""
import requests
import json
import sys

API_BASE = "http://localhost:8000/api"

def get_auth_token():
    """Get authentication token"""
    # Try to login
    login_data = {
        "username": "admin",  # Change if needed
        "password": "admin"   # Change if needed
    }
    
    try:
        response = requests.post(f"{API_BASE}/auth/token/", json=login_data)
        if response.status_code == 200:
            return response.json().get('access')
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error getting token: {e}")
        return None

def test_service_check():
    """Test creating and running a service check"""
    token = get_auth_token()
    if not token:
        print("Could not get auth token. Please check credentials.")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # First, get hosts
    print("\n1. Getting hosts...")
    try:
        response = requests.get(f"{API_BASE}/inventory/hosts/", headers=headers)
        if response.status_code == 200:
            hosts = response.json()
            if isinstance(hosts, dict) and 'results' in hosts:
                hosts = hosts['results']
            elif not isinstance(hosts, list):
                hosts = []
            
            print(f"   Found {len(hosts)} hosts")
            if len(hosts) == 0:
                print("   No hosts found. Please create a host first.")
                return
            
            # Use first host
            host = hosts[0]
            host_id = host['id']
            print(f"   Using host: {host.get('hostname', 'N/A')} (ID: {host_id})")
        else:
            print(f"   Failed to get hosts: {response.status_code}")
            return
    except Exception as e:
        print(f"   Error getting hosts: {e}")
        return
    
    # Check if service check already exists
    print("\n2. Checking existing service checks...")
    try:
        response = requests.get(f"{API_BASE}/monitoring/configs/?host={host_id}", headers=headers)
        if response.status_code == 200:
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
            
            if ping_check:
                print(f"   Found existing ping check (ID: {ping_check['id']})")
                check_id = ping_check['id']
            else:
                print("   No ping check found, creating one...")
                # Create a ping service check
                check_data = {
                    "host": host_id,
                    "check_type": "ping",
                    "check_name": "Test Ping Check",
                    "enabled": True,
                    "interval": 60,
                    "timeout": 10,
                    "parameters": {"count": 3}
                }
                
                response = requests.post(f"{API_BASE}/monitoring/configs/", 
                                        headers=headers, json=check_data)
                if response.status_code in [200, 201]:
                    check_id = response.json()['id']
                    print(f"   Created ping check (ID: {check_id})")
                else:
                    print(f"   Failed to create check: {response.status_code} - {response.text}")
                    return
        else:
            print(f"   Failed to get checks: {response.status_code}")
            return
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    # Run the check
    print(f"\n3. Running service check (ID: {check_id})...")
    try:
        response = requests.post(f"{API_BASE}/monitoring/configs/{check_id}/run/", headers=headers)
        if response.status_code == 202:
            print("   Check queued successfully")
        else:
            print(f"   Failed to queue check: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   Error running check: {e}")
    
    # Wait a moment and check results
    import time
    print("\n4. Waiting 3 seconds for check to complete...")
    time.sleep(3)
    
    # Get check status
    print("\n5. Checking service check status...")
    try:
        response = requests.get(f"{API_BASE}/monitoring/configs/{check_id}/", headers=headers)
        if response.status_code == 200:
            check = response.json()
            print(f"   Status: {check.get('status', 'N/A')}")
            print(f"   Last Output: {check.get('last_output', 'N/A')}")
            print(f"   Last Check: {check.get('last_check', 'N/A')}")
            
            if check.get('status') == 'unknown':
                print("\n   ⚠️  WARNING: Status is 'unknown' - check may not have executed")
                print("   This could mean Celery worker is not running")
            elif check.get('status') in ['ok', 'critical']:
                print("\n   ✓ Check executed successfully!")
        else:
            print(f"   Failed to get check status: {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Get recent results
    print("\n6. Getting recent check results...")
    try:
        response = requests.get(f"{API_BASE}/monitoring/results/?service_check={check_id}", headers=headers)
        if response.status_code == 200:
            results = response.json()
            if isinstance(results, dict) and 'results' in results:
                results = results['results']
            elif not isinstance(results, list):
                results = []
            
            print(f"   Found {len(results)} result(s)")
            if results:
                latest = results[0]
                print(f"   Latest Result:")
                print(f"     Status: {latest.get('status', 'N/A')}")
                print(f"     Output: {latest.get('output', 'N/A')}")
                print(f"     Response Time: {latest.get('response_time', 'N/A')}ms")
                print(f"     Timestamp: {latest.get('timestamp', 'N/A')}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_service_check()
