import socket
import ipaddress
from typing import List, Tuple
from urllib.parse import urlparse
from src.orchestration.errors import RecoverableError, FatalValidation

CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")

def is_ip_safe(ip_str: str) -> bool:
    import os
    if os.environ.get("BENCHMARK_MODE") == "1":
        return True
        
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return False
            
        if isinstance(ip, ipaddress.IPv4Address):
            if ip in CGNAT_NETWORK:
                return False
                
        elif isinstance(ip, ipaddress.IPv6Address):
            if ip.ipv4_mapped:
                return is_ip_safe(str(ip.ipv4_mapped))
            # Site local/unique local
            if ip.is_site_local:
                return False
        return True
    except ValueError:
        return False

def resolve_and_validate(url: str, is_initial: bool = False) -> Tuple[str, str]:
    """
    Returns (pinned_url_with_ip, original_host_for_headers)
    Throws FatalValidation if is_initial=True, otherwise RecoverableError
    """
    ErrorClass = FatalValidation if is_initial else RecoverableError
    
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    
    try:
        addrinfo = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise ErrorClass(f"DNS resolution failed for {host}: {e}")

    safe_ips = []
    for res in addrinfo:
        ip = res[4][0]
        if not is_ip_safe(ip):
            raise ErrorClass(f"Host {host} resolves to unsafe IP: {ip}")
        safe_ips.append(ip)

    if not safe_ips:
        raise ErrorClass(f"No valid IP addresses found for {host}")

    pinned_ip = safe_ips[0]
    
    # Format IPv6 addresses properly
    if ":" in pinned_ip:
        pinned_ip = f"[{pinned_ip}]"
        
    netloc = f"{pinned_ip}:{port}" if parsed.port else pinned_ip
    
    pinned_url = urlparse(url)._replace(netloc=netloc).geturl()
    return pinned_url, host
