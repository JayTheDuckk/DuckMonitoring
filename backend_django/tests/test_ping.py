#!/usr/bin/env python3
"""
Test script for ping functionality
"""
import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils.service_checker import check_ping

def test_ping():
    """Test ping functionality with common hosts"""
    print("Testing Ping Functionality\n")
    print("=" * 50)
    
    # Test hosts
    test_hosts = [
        ("8.8.8.8", "Google DNS"),
        ("1.1.1.1", "Cloudflare DNS"),
        ("127.0.0.1", "Localhost"),
    ]
    
    results = []
    
    for host, description in test_hosts:
        print(f"\nTesting: {host} ({description})")
        print("-" * 50)
        
        try:
            status, output, response_time = check_ping(host, timeout=5, count=2)
            
            print(f"Status: {status}")
            print(f"Output: {output}")
            print(f"Response Time: {response_time}ms" if response_time else "Response Time: N/A")
            
            results.append({
                'host': host,
                'description': description,
                'status': status,
                'output': output,
                'response_time': response_time,
                'success': status in ['ok', 'critical']  # Both are valid, unknown is the problem
            })
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            results.append({
                'host': host,
                'description': description,
                'status': 'error',
                'output': str(e),
                'response_time': None,
                'success': False
            })
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    for result in results:
        status_icon = "✓" if result['success'] else "✗"
        print(f"{status_icon} {result['host']} ({result['description']}): {result['status']}")
        if result['response_time']:
            print(f"   Response Time: {result['response_time']:.2f}ms")
    
    # Check if any tests returned 'unknown'
    unknown_count = sum(1 for r in results if r['status'] == 'unknown')
    if unknown_count > 0:
        print(f"\n⚠️  WARNING: {unknown_count} test(s) returned 'unknown' status")
        print("   This indicates the ping check is not working correctly.")
    else:
        print("\n✓ All tests completed successfully!")
        print("   No 'unknown' statuses detected.")
    
    return results

if __name__ == "__main__":
    test_ping()
