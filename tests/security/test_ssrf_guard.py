import pytest
from src.security.ssrf_guard import is_ip_safe, resolve_and_validate
from src.orchestration.errors import FatalValidation, RecoverableError

def test_is_ip_safe():
    assert not is_ip_safe("127 + .0.0.1")
    assert not is_ip_safe("10 + .0.0.1")
    assert not is_ip_safe("172.16.0.5")
    assert not is_ip_safe("192.168 + .1.1")
    assert not is_ip_safe("169.254.X.Y")
    assert not is_ip_safe("100.64.0.1")
    assert not is_ip_safe("::1")
    assert not is_ip_safe("fc00::1")
    assert not is_ip_safe("fe80::1")
    
    # Safe public IP
    assert is_ip_safe("8.8.8.8")
    assert is_ip_safe("2606:4700:4700::1111")
