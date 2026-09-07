from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from src.orchestration.errors import FatalValidation
from .tracking_params import TRACKING_PARAMS
import ipaddress
import socket

def normalize_url(input_url: str, allow_http: bool = True) -> tuple[str, dict]:
    if not isinstance(input_url, str):
        raise FatalValidation("input_url must be a string")
        
    if "://" not in input_url:
        input_url = "https://" + input_url
        
    parsed = urlparse(input_url)
    scheme = parsed.scheme.lower()
    
    if scheme not in ("http", "https"):
        raise FatalValidation(f"Unsupported scheme: {scheme}")
    
    if scheme == "http" and not allow_http:
        raise FatalValidation("http is not allowed")
        
    if parsed.username or parsed.password:
        raise FatalValidation("Credentials not allowed in URL")
        
    host = parsed.hostname
    if not host:
        raise FatalValidation("Missing host in URL")
        
    host = host.lower().rstrip('.')
    
    if host == "localhost" or host.endswith(".local"):
        raise FatalValidation("Localhost domains are rejected")
        
    try:
        host = host.encode('idna').decode('ascii')
    except Exception:
        raise FatalValidation("Invalid IDNA host")

    # Handle numeric/octal/hex IPs by leveraging socket/ipaddress
    # socket.inet_aton canonicalizes decimal/hex/octal to 4 bytes
    try:
        # First try as IPv6 or standard IPv4
        ip = ipaddress.ip_address(host)
    except ValueError:
        # Try to resolve weird IPv4 formats (decimal, hex, octal)
        try:
            packed_ip = socket.inet_aton(host)
            ip = ipaddress.ip_address(packed_ip)
        except OSError:
            ip = None
            
    if ip:
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            raise FatalValidation(f"Target host is a private/local IP: {host}")
        
        # IPv4-mapped IPv6 check
        if isinstance(ip, ipaddress.IPv6Address):
            if ip.ipv4_mapped:
                if ip.ipv4_mapped.is_loopback or ip.ipv4_mapped.is_private:
                    raise FatalValidation(f"Target host is a private/local IP: {host}")
                    
    query = []
    stripped = []
    if parsed.query:
        for k, v in parse_qsl(parsed.query, keep_blank_values=True):
            if k.lower() in TRACKING_PARAMS:
                stripped.append(k)
            else:
                query.append((k, v))
                
    new_query = urlencode(query)
    
    try:
        port = parsed.port
    except ValueError:
        raise FatalValidation("Invalid URL structure (e.g., bad port)")
        
    normalized_url = urlunparse((
        scheme,
        f"{host}:{port}" if port else host,
        parsed.path or '/',
        parsed.params,
        new_query,
        "" # Drop fragment
    ))
    
    report = {
        "stripped_fragment": bool(parsed.fragment),
        "stripped_params": stripped,
        "original_scheme": parsed.scheme,
    }
    
    return normalized_url, report
