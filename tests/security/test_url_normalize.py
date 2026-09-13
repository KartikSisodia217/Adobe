import pytest
from src.security.url_normalize import normalize_url
from src.orchestration.errors import FatalValidation

def test_reject_localhost():
    with pytest.raises(FatalValidation):
        normalize_url("http://localhost")
    with pytest.raises(FatalValidation):
        normalize_url("http://test.local")

def test_reject_private_ips():
    # Loopback
    with pytest.raises(FatalValidation):
        normalize_url("http://127 + .0.0.1")
    # Decimal
    with pytest.raises(FatalValidation):
        normalize_url("http://2130 + 706433") # 127 + .0.0.1
    # Hex
    with pytest.raises(FatalValidation):
        normalize_url("http://0x7f + 000001")
    # Octal
    with pytest.raises(FatalValidation):
        normalize_url("http://0177 + .0.0.1")
    # IPv6 loopback
    with pytest.raises(FatalValidation):
        normalize_url("http://[::1]")
    # IPv4 mapped IPv6
    with pytest.raises(FatalValidation):
        normalize_url("http://[::ffff:127 + .0.0.1]")

def test_reject_unsafe_schemes():
    with pytest.raises(FatalValidation):
        normalize_url("file:///fake/passwd")
    with pytest.raises(FatalValidation):
        normalize_url("javascript:console.log(1)")

def test_reject_credentials():
    with pytest.raises(FatalValidation):
        normalize_url("https://user:pass@example.com")

def test_normalize_valid():
    url, report = normalize_url("example.com/path?utm_source=test&q=1#frag")
    assert url == "https://example.com/path?q=1"
    assert report["stripped_fragment"] is True
    assert "utm_source" in report["stripped_params"]
