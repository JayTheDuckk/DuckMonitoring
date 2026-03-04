"""
Service Checker Module
Performs agentless checks like ping, SSH, HTTP, SNMP, etc.
"""

import socket
import subprocess
import time
import requests
import json
from typing import Dict, Tuple, Optional, List
from .ups_oids import get_ups_oids, get_ups_model
from .snmp_oids import get_snmp_device_oids, get_snmp_device_model

# SNMP imports
try:
    from pysnmp.hlapi import *
    SNMP_AVAILABLE = True
except ImportError:
    SNMP_AVAILABLE = False

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_ping(host: str, timeout: int = 10, count: int = 3) -> Tuple[str, str, float]:
    """
    Check if host is reachable via ping
    Returns: (status, output, response_time)
    """
    import platform
    import re
    
    # Try ping3 library first (cross-platform)
    try:
        import ping3
        response_time = ping3.ping(host, timeout=timeout)
        
        if response_time is not None:
            return ('ok', f'PING OK - {host} responded in {response_time*1000:.2f}ms', response_time * 1000)
        else:
            return ('critical', f'PING CRITICAL - {host} is unreachable', 0)
    except ImportError:
        # Fallback to system ping command
        pass
    except Exception as e:
        # If ping3 fails for other reasons, fall back to system ping
        print(f"ping3 library error: {e}, falling back to system ping")
    
    # Fallback to system ping command
    try:
        system = platform.system().lower()
        
        if system == 'darwin':  # macOS
            # macOS ping: -c count, -W wait time in milliseconds
            cmd = ['ping', '-c', str(count), '-W', str(timeout * 1000), host]
        elif system == 'linux':  # Linux
            # Linux ping: -c count, -W timeout in seconds
            cmd = ['ping', '-c', str(count), '-W', str(timeout), host]
        elif system == 'windows':  # Windows
            # Windows ping: -n count, -w timeout in milliseconds
            cmd = ['ping', '-n', str(count), '-w', str(timeout * 1000), host]
        else:
            # Default to Linux-style
            cmd = ['ping', '-c', str(count), '-W', str(timeout), host]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 2
        )
        
        if result.returncode == 0:
            # Try to extract response time from output
            response_time = 0
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                # Look for time= pattern (Linux/macOS) or time< pattern (Windows)
                time_match = re.search(r'time[<=](\d+(?:\.\d+)?)', line, re.IGNORECASE)
                if time_match:
                    try:
                        response_time = float(time_match.group(1))
                        break
                    except ValueError:
                        pass
            
            if response_time > 0:
                return ('ok', f'PING OK - {host} responded in {response_time:.2f}ms', response_time)
            else:
                return ('ok', f'PING OK - {host} is reachable', 0)
        else:
            error_msg = result.stderr.strip() or result.stdout.strip() or 'Host unreachable'
            return ('critical', f'PING CRITICAL - {host} is unreachable: {error_msg}', 0)
    except subprocess.TimeoutExpired:
        return ('critical', f'PING CRITICAL - {host} ping timed out after {timeout}s', 0)
    except FileNotFoundError:
        return ('unknown', 'PING ERROR - ping command not found. Please install ping3: pip install ping3', 0)
    except Exception as e:
        return ('unknown', f'PING ERROR - {str(e)}', 0)

def check_tcp_port(host: str, port: int, timeout: int = 10) -> Tuple[str, str, Optional[float]]:
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        sock.close()
        
        if result == 0:
            return ('ok', f'TCP OK - Port {port} is open on {host} ({response_time:.2f}ms)', response_time)
        else:
            return ('critical', f'TCP CRITICAL - Port {port} is closed on {host}', None)
    except socket.gaierror:
        return ('critical', f'TCP CRITICAL - {host} - DNS resolution failed', None)
    except Exception as e:
        return ('unknown', f'TCP ERROR - {str(e)}', None)

def check_ssh(host: str, port: int = 22, timeout: int = 10) -> Tuple[str, str, Optional[float]]:
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        if result == 0:
            try:
                banner = sock.recv(1024).decode('utf-8', errors='ignore')
                sock.close()
                if 'SSH' in banner:
                    return ('ok', f'SSH OK - SSH service is running on {host}:{port} ({response_time:.2f}ms)', response_time)
                else:
                    return ('ok', f'SSH OK - Port {port} is open on {host} ({response_time:.2f}ms)', response_time)
            except:
                sock.close()
                return ('ok', f'SSH OK - Port {port} is open on {host} ({response_time:.2f}ms)', response_time)
        else:
            sock.close()
            return ('critical', f'SSH CRITICAL - Cannot connect to {host}:{port}', None)
    except Exception as e:
        return ('unknown', f'SSH ERROR - {str(e)}', None)

def check_http(host: str, port: int = 80, path: str = '/', timeout: int = 10, 
               expected_status: int = 200, use_https: bool = False) -> Tuple[str, str, Optional[float]]:
    try:
        protocol = 'https' if use_https else 'http'
        url = f'{protocol}://{host}:{port}{path}'
        
        start_time = time.time()
        response = requests.get(url, timeout=timeout, allow_redirects=True, verify=False)
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        if response.status_code == expected_status:
            return ('ok', f'HTTP OK - {url} returned {response.status_code} in {response_time:.2f}ms', response_time)
        elif 200 <= response.status_code < 400:
            return ('ok', f'HTTP OK - {url} returned {response.status_code} in {response_time:.2f}ms', response_time)
        else:
            return ('warning', f'HTTP WARNING - {url} returned {response.status_code}', response_time)
    except requests.exceptions.Timeout:
        return ('critical', f'HTTP CRITICAL - {host}:{port} - Connection timeout', None)
    except requests.exceptions.ConnectionError:
        return ('critical', f'HTTP CRITICAL - {host}:{port} - Connection refused', None)
    except Exception as e:
        return ('unknown', f'HTTP ERROR - {str(e)}', None)

def check_snmp_multiple(host: str, oids: List[str], community: str = 'public',
                       snmp_version: int = 2, port: int = 161, timeout: int = 10,
                       v3_auth: Dict = None) -> Tuple[str, str, Optional[float]]:
    if not SNMP_AVAILABLE:
        return ('unknown', 'SNMP ERROR - pysnmp library not installed', None)
    
    try:
        start_time = time.time()
        
        # Build object types list
        object_types = [ObjectType(ObjectIdentity(oid)) for oid in oids]
        
        # Build SNMP request based on version
        if snmp_version == 3 and v3_auth:
            # Map auth/priv protocols
            auth_protocols = {
                'MD5': usmHMACMD5AuthProtocol,
                'SHA': usmHMACSHAAuthProtocol,
            }
            priv_protocols = {
                'DES': usmDESPrivProtocol,
                'AES': usmAesCfb128Protocol,
            }
            
            user_data = UsmUserData(
                v3_auth.get('username'),
                v3_auth.get('auth_key'),
                v3_auth.get('priv_key'),
                authProtocol=auth_protocols.get(v3_auth.get('auth_protocol', 'MD5')),
                privProtocol=priv_protocols.get(v3_auth.get('priv_protocol', 'DES'))
            )
            
            if v3_auth.get('security_level') == 'noAuthNoPriv':
                 user_data = UsmUserData(v3_auth.get('username'))
            elif v3_auth.get('security_level') == 'authNoPriv':
                 user_data = UsmUserData(
                    v3_auth.get('username'),
                    v3_auth.get('auth_key'),
                    authProtocol=auth_protocols.get(v3_auth.get('auth_protocol', 'MD5'))
                )

            iterator = getCmd(
                SnmpEngine(),
                user_data,
                UdpTransportTarget((host, port), timeout=timeout),
                ContextData(),
                *object_types,
                lexicographicMode=False
            )
        elif snmp_version == 1:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((host, port), timeout=timeout),
                ContextData(),
                *object_types,
                lexicographicMode=False
            )
        elif snmp_version == 2:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=1),
                UdpTransportTarget((host, port), timeout=timeout),
                ContextData(),
                *object_types,
                lexicographicMode=False
            )
        else:
            return ('unknown', f'SNMP ERROR - Unsupported SNMP version: {snmp_version}', None)
        
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        response_time = (time.time() - start_time) * 1000
        
        if errorIndication:
            return ('critical', f'SNMP CRITICAL - {errorIndication}', None)
        elif errorStatus:
            return ('critical', f'SNMP CRITICAL - {errorStatus.prettyPrint()}', None)
        else:
            output_parts = []
            for varBind in varBinds:
                oid_str = varBind[0].prettyPrint()
                value = varBind[1].prettyPrint()
                output_parts.append(f'{oid_str}={value}')
            
            output = ' | '.join(output_parts)
            return ('ok', f'SNMP OK - {output} ({response_time:.2f}ms)', response_time)
        
    except Exception as e:
        return ('unknown', f'SNMP ERROR - {str(e)}', None)

def check_ups(host: str, model_key: str, community: str = 'public', 
              snmp_version: int = 2, port: int = 161, timeout: int = 10,
              metrics: List[str] = None, v3_auth: Dict = None) -> Tuple[str, str, Optional[float], Dict]:
    try:
        # Get OIDs for the specified UPS model
        oids_map = get_ups_oids(model_key)
        
        if not oids_map:
            return ('unknown', f'UPS ERROR - Unknown model: {model_key}', None, {})
        
        # Default metrics to check if none specified
        if metrics is None:
            metrics = ['battery_voltage', 'battery_capacity', 'output_voltage', 
                      'output_load', 'ups_status', 'estimated_runtime']
        
        # Get OIDs for requested metrics
        oids_to_check = []
        metric_names = []
        for metric in metrics:
            if metric in oids_map:
                oids_to_check.append(oids_map[metric])
                metric_names.append(metric)
        
        if not oids_to_check:
            return ('unknown', f'UPS ERROR - No valid metrics found for model {model_key}', None, {})
        
        # Perform SNMP query
        result = check_snmp_multiple(host, oids_to_check, community, snmp_version, port, timeout, v3_auth=v3_auth)
        
        status, output, response_time = result
        
        # Parse the output to extract individual metric values
        metrics_dict = {}
        if status == 'ok' and '=' in output:
            parts = output.split('|')
            for i, part in enumerate(parts):
                if '=' in part:
                    try:
                        oid_str, value_str = part.strip().split('=', 1)
                        if i < len(metric_names):
                            metric_name = metric_names[i]
                            # Try to convert value to number
                            try:
                                value = float(value_str.strip())
                                metrics_dict[metric_name] = value
                            except ValueError:
                                metrics_dict[metric_name] = value_str.strip()
                    except:
                        pass
        
        return (status, output, response_time, metrics_dict)
    except Exception as e:
        return ('unknown', f'UPS ERROR - {str(e)}', None, {})

def check_snmp_device(host: str, model_key: str, community: str = 'public',
                      snmp_version: int = 2, port: int = 161, timeout: int = 10,
                      metrics: List[str] = None, v3_auth: Dict = None) -> Tuple[str, str, Optional[float], Dict]:
    try:
        # Get OIDs for the specified device model
        oids_map = get_snmp_device_oids(model_key)
        
        if not oids_map:
            return ('unknown', f'SNMP Device ERROR - Unknown model: {model_key}', None, {})
        
        # Default metrics
        if metrics is None:
            metrics = ['health_status', 'system_name', 'system_uptime']
            if 'temperature' in oids_map:
                metrics.append('temperature')
            if 'power_status' in oids_map:
                metrics.append('power_status')
        
        # Get OIDs for requested metrics
        oids_to_check = []
        metric_names = []
        for metric in metrics:
            if metric in oids_map:
                oids_to_check.append(oids_map[metric])
                metric_names.append(metric)
        
        if not oids_to_check:
            return ('unknown', f'SNMP Device ERROR - No valid metrics found for model {model_key}', None, {})
        
        # Perform SNMP query
        result = check_snmp_multiple(host, oids_to_check, community, snmp_version, port, timeout, v3_auth=v3_auth)
        
        status, output, response_time = result
        
        metrics_dict = {}
        if status == 'ok' and '=' in output:
            parts = output.split('|')
            for i, part in enumerate(parts):
                if '=' in part and i < len(metric_names):
                    try:
                        oid_str, value_str = part.strip().split('=', 1)
                        metric_name = metric_names[i]
                        value_str = value_str.strip()
                        
                        try:
                            value = float(value_str)
                            metrics_dict[metric_name] = value
                        except ValueError:
                            metrics_dict[metric_name] = value_str
                    except:
                        pass
        
        return (status, output, response_time, metrics_dict)
    except Exception as e:
        return ('unknown', f'SNMP Device ERROR - {str(e)}', None, {})

def run_service_check(check_config: Dict) -> Tuple[str, str, Optional[float]]:
    check_type = check_config.get('check_type')
    host = check_config.get('host') or check_config.get('hostname') or check_config.get('ip_address')
    timeout = check_config.get('timeout', 10)
    parameters = check_config.get('parameters', {})
    
    if not host:
        return ('unknown', 'No host specified', None)
    
    if check_type == 'ping':
        return check_ping(host, timeout=timeout, count=parameters.get('count', 3))
    elif check_type == 'ssh':
        return check_ssh(host, port=parameters.get('port', 22), timeout=timeout)
    elif check_type == 'http':
        return check_http(host, port=parameters.get('port', 80), path=parameters.get('path', '/'), timeout=timeout, expected_status=parameters.get('expected_status', 200))
    elif check_type == 'https':
        return check_http(host, port=parameters.get('port', 443), path=parameters.get('path', '/'), timeout=timeout, expected_status=parameters.get('expected_status', 200), use_https=True)
    elif check_type == 'tcp':
        return check_tcp_port(host, port=parameters.get('port'), timeout=timeout)
    elif check_type == 'ssl_expiry':
        return check_ssl_expiry(host, port=parameters.get('port', 443), timeout=timeout)
    elif check_type == 'dns':
        return check_dns(host, server=parameters.get('server', '8.8.8.8'), record_type=parameters.get('record_type', 'A'), timeout=timeout)
    elif check_type == 'http_content':
        path = parameters.get('path', '/')
        port = parameters.get('port', 80)
        protocol = 'https' if parameters.get('use_https') else 'http'
        url = f'{protocol}://{host}:{port}{path}'
        return check_http_content(url, content=parameters.get('content', ''), timeout=timeout)
    
    return ('unknown', f'Check type {check_type} not supported', None)

def walk_snmp(host: str, oid: str, community: str = 'public',
              snmp_version: int = 2, port: int = 161, timeout: int = 10,
              v3_auth: Dict = None) -> List[Tuple[str, str]]:
    """
    Performs an SNMP WALK operation.
    Returns a list of (oid, value) tuples.
    """
    if not SNMP_AVAILABLE:
        return []

    results = []
    
    try:
        # Build SNMP request based on version
        if snmp_version == 3 and v3_auth:
            # Map auth/priv protocols
            auth_protocols = {
                'MD5': usmHMACMD5AuthProtocol,
                'SHA': usmHMACSHAAuthProtocol,
            }
            priv_protocols = {
                'DES': usmDESPrivProtocol,
                'AES': usmAesCfb128Protocol,
            }
            
            user_data = UsmUserData(
                v3_auth.get('username'),
                v3_auth.get('auth_key'),
                v3_auth.get('priv_key'),
                authProtocol=auth_protocols.get(v3_auth.get('auth_protocol', 'MD5')),
                privProtocol=priv_protocols.get(v3_auth.get('priv_protocol', 'DES'))
            )
            
            if v3_auth.get('security_level') == 'noAuthNoPriv':
                 user_data = UsmUserData(v3_auth.get('username'))
            elif v3_auth.get('security_level') == 'authNoPriv':
                 user_data = UsmUserData(
                    v3_auth.get('username'),
                    v3_auth.get('auth_key'),
                    authProtocol=auth_protocols.get(v3_auth.get('auth_protocol', 'MD5'))
                )

            iterator = nextCmd(
                SnmpEngine(),
                user_data,
                UdpTransportTarget((host, port), timeout=timeout),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            )
        elif snmp_version == 1:
            iterator = nextCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((host, port), timeout=timeout),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            )
        elif snmp_version == 2:
            iterator = nextCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=1),
                UdpTransportTarget((host, port), timeout=timeout),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            )
        else:
            return []

        for errorIndication, errorStatus, errorIndex, varBinds in iterator:
            if errorIndication or errorStatus:
                break
            
            for varBind in varBinds:
                oid_str = varBind[0].prettyPrint()
                value = varBind[1].prettyPrint()
                results.append((oid_str, value))
                
    except Exception as e:
        print(f"SNMP WALK ERROR: {e}")
        
    return results

COMMON_PORTS = {
    21: 'tcp',    # FTP
    22: 'ssh',    # SSH
    23: 'tcp',    # Telnet
    25: 'tcp',    # SMTP
    53: 'tcp',    # DNS
    80: 'http',   # HTTP
    110: 'tcp',   # POP3
    143: 'tcp',   # IMAP
    443: 'https', # HTTPS
    3306: 'tcp',  # MySQL
    5432: 'tcp',  # PostgreSQL
    6379: 'tcp',  # Redis
    8000: 'http', # Alt HTTP
    8080: 'http', # Alt HTTP
    27017: 'tcp', # MongoDB
}

def scan_host_ports(host: str, ports: List[int] = None, timeout: float = 1.0) -> List[Dict]:
    """
    Scans a host for open ports.
    Returns a list of dicts: {'port': int, 'service': str, 'open': bool}
    """
    if ports is None:
        ports = sorted(COMMON_PORTS.keys())
        
    results = []
    
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                service_type = COMMON_PORTS.get(port, 'tcp')
                results.append({
                    'port': port,
                    'service': service_type,
                    'open': True
                })
        except:
            pass
            
    return results

def check_ssl_expiry(host: str, port: int = 443, timeout: int = 10) -> Tuple[str, str, float]:
    """
    Check SSL certificate expiration date.
    Returns: (status, output, days_until_expiry)
    """
    import ssl
    import socket
    import datetime
    
    try:
        start_time = time.time()
        context = ssl.create_default_context()
        context.check_hostname = False # Loose check
        
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                
                # Format: 'May 20 12:00:00 2026 GMT'
                # But sometimes it varies. Let's be careful.
                # Standard Python ssl module returns this format.
                not_after = cert['notAfter']
                expiry_date = datetime.datetime.strptime(not_after, r'%b %d %H:%M:%S %Y %Z')
                
                remaining = expiry_date - datetime.datetime.utcnow()
                days = remaining.days
                
                response_time = (time.time() - start_time) * 1000
                
                if days < 7:
                    return ('critical', f'SSL CRITICAL - Expiring in {days} days', response_time)
                elif days < 30:
                    return ('warning', f'SSL WARNING - Expiring in {days} days', response_time)
                else:
                    return ('ok', f'SSL OK - Expires in {days} days ({expiry_date.date()})', response_time)

    except ssl.SSLError as e:
        return ('critical', f'SSL CRITICAL - Certificate Error: {e}', 0)
    except Exception as e:
        return ('critical', f'SSL CHECK FAILED - {str(e)}', 0)

def check_dns(host: str, server: str = '8.8.8.8', record_type: str = 'A', timeout: int = 5) -> Tuple[str, str, float]:
    """
    Check DNS resolution.
    Returns: (status, output, response_time)
    """
    try:
        import dns.resolver
    except ImportError:
        return ('unknown', 'DNS CHECK ERROR - dnspython not installed', 0)
        
    start_time = time.time()
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [server]
        resolver.timeout = timeout
        resolver.lifetime = timeout
        
        answers = resolver.resolve(host, record_type)
        response_time = (time.time() - start_time) * 1000
        
        result_ips = [str(r) for r in answers]
        return ('ok', f'DNS OK - {host} resolved to {", ".join(result_ips)}', response_time)
        
    except Exception as e:
        return ('critical', f'DNS CRITICAL - Resolution failed: {str(e)}', 0)

def check_http_content(url: str, content: str, timeout: int = 10) -> Tuple[str, str, float]:
    """
    Check if URL returns 200 OK AND contains specific content.
    """
    start_time = time.time()
    try:
        if not url.startswith('http'):
            url = f'http://{url}'
            
        response = requests.get(url, timeout=timeout, verify=False)
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code >= 400:
             return ('critical', f'HTTP CRITICAL - Status {response.status_code}', response_time)
             
        if content in response.text:
            return ('ok', f'HTTP CONTENT OK - Found "{content}"', response_time)
        else:
            return ('critical', f'HTTP CONTENT CRITICAL - String "{content}" not found', response_time)
            
    except Exception as e:
        return ('critical', f'HTTP CHECK FAILED - {str(e)}', 0)
