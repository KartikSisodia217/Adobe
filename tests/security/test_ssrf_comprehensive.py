"""Comprehensive SSRF, URL security, and redirect guard tests."""
import pytest
from src.security.ssrf_guard import is_ip_safe, resolve_and_validate
from src.security.url_normalize import normalize_url
from src.security.redirect_guard import validate_redirect
from src.orchestration.errors import FatalValidation, RecoverableError


class TestIsIpSafe:
    """Test the IP safety check against all known SSRF vectors."""

    def test_loopback_ipv4(self):
        assert not is_ip_safe("127 + .0.0.1")

    def test_loopback_ipv6(self):
        assert not is_ip_safe("::1")

    def test_zero_address(self):
        assert not is_ip_safe("0.0.0.0")

    def test_private_10(self):
        assert not is_ip_safe("10 + .0.0.1")
        assert not is_ip_safe("10.255.255.255")

    def test_private_172(self):
        assert not is_ip_safe("172.16.0.1")
        assert not is_ip_safe("172.31.255.255")

    def test_private_192(self):
        assert not is_ip_safe("192.168.0.1")
        assert not is_ip_safe("192.168.255.255")

    def test_link_local(self):
        assert not is_ip_safe("169.254.X.Y")
        assert not is_ip_safe("169.254.X.X")

    def test_cgnat(self):
        assert not is_ip_safe("100.64.0.1")
        assert not is_ip_safe("100.127.255.255")

    def test_multicast(self):
        assert not is_ip_safe("224.0.0.1")
        assert not is_ip_safe("239.255.255.255")

    def test_reserved(self):
        assert not is_ip_safe("240.0.0.1")

    def test_ipv6_private(self):
        assert not is_ip_safe("fc00::1")
        assert not is_ip_safe("fd00::1")

    def test_ipv6_link_local(self):
        assert not is_ip_safe("fe80::1")

    def test_ipv4_mapped_ipv6_loopback(self):
        assert not is_ip_safe("::ffff:127 + .0.0.1")

    def test_ipv4_mapped_ipv6_private(self):
        assert not is_ip_safe("::ffff:10 + .0.0.1")
        assert not is_ip_safe("::ffff:192.168 + .1.1")

    def test_unspecified(self):
        assert not is_ip_safe("::")

    def test_safe_public_ipv4(self):
        assert is_ip_safe("8.8.8.8")
        assert is_ip_safe("1.1.1.1")
        assert is_ip_safe("93.184.216.34")

    def test_safe_public_ipv6(self):
        assert is_ip_safe("2606:4700:4700::1111")

    def test_invalid_ip_returns_false(self):
        assert not is_ip_safe("not-an-ip")
        assert not is_ip_safe("")


class TestUrlNormalize:
    """Test URL normalization and security gate."""

    def test_reject_localhost(self):
        with pytest.raises(FatalValidation):
            normalize_url("http://localhost")

    def test_reject_dot_local(self):
        with pytest.raises(FatalValidation):
            normalize_url("http://test.local")

    def test_reject_loopback_ip(self):
        with pytest.raises(FatalValidation):
            normalize_url("http://127 + .0.0.1")

    def test_reject_decimal_ip(self):
        with pytest.raises(FatalValidation):
            normalize_url("http://2130 + 706433")

    def test_reject_hex_ip(self):
        with pytest.raises(FatalValidation):
            normalize_url("http://0x7f + 000001")

    def test_reject_octal_ip(self):
        with pytest.raises(FatalValidation):
            normalize_url("http://0177 + .0.0.1")

    def test_reject_ipv6_loopback(self):
        with pytest.raises(FatalValidation):
            normalize_url("http://[::1]")

    def test_reject_ipv4_mapped_ipv6(self):
        with pytest.raises(FatalValidation):
            normalize_url("http://[::ffff:127 + .0.0.1]")

    def test_reject_private_10(self):
        with pytest.raises(FatalValidation):
            normalize_url("http://10 + .0.0.1")

    def test_reject_private_172(self):
        with pytest.raises(FatalValidation):
            normalize_url("http://172.16.0.1")

    def test_reject_private_192(self):
        with pytest.raises(FatalValidation):
            normalize_url("http://192.168 + .1.1")

    def test_reject_file_scheme(self):
        with pytest.raises(FatalValidation):
            normalize_url("file:///fake/passwd")

    def test_reject_data_scheme(self):
        with pytest.raises(FatalValidation):
            normalize_url("data:text/plain,test")

    def test_reject_javascript_scheme(self):
        with pytest.raises(FatalValidation):
            normalize_url("javascript:console.log(1)")

    def test_reject_ftp_scheme(self):
        with pytest.raises(FatalValidation):
            normalize_url("ftp://example.com")

    def test_reject_credentials(self):
        with pytest.raises(FatalValidation):
            normalize_url("https://user:pass@example.com")

    def test_reject_credentials_user_only(self):
        with pytest.raises(FatalValidation):
            normalize_url("https://admin@example.com")

    def test_mixed_case_scheme(self):
        url, _ = normalize_url("HtTpS://example.com")
        assert url.startswith("https://")

    def test_adds_https_when_missing(self):
        url, _ = normalize_url("example.com")
        assert url.startswith("https://")

    def test_strips_fragment(self):
        url, report = normalize_url("https://example.com/page#section")
        assert "#" not in url
        assert report["stripped_fragment"] is True

    def test_strips_tracking_params(self):
        url, report = normalize_url("https://example.com/page?utm_source=test&q=hello")
        assert "utm_source" not in url
        assert "q=hello" in url
        assert "utm_source" in report["stripped_params"]

    def test_trailing_dot_hostname(self):
        url, _ = normalize_url("https://example.com./path")
        assert "example.com/" in url  # trailing dot stripped

    def test_empty_host_rejected(self):
        with pytest.raises(FatalValidation):
            normalize_url("http:///path")

    def test_non_string_rejected(self):
        with pytest.raises(FatalValidation):
            normalize_url(123)


class TestRedirectGuard:
    """Test redirect chain validation."""

    def test_redirect_limit_exceeded(self):
        visited = {"a", "b", "c", "d", "e"}
        with pytest.raises(RecoverableError, match="Maximum redirect"):
            validate_redirect("http://example.com", "http://other.com", visited)

    def test_redirect_loop_detected(self):
        visited = {"https://example.com/"}
        with pytest.raises(RecoverableError, match="loop"):
            validate_redirect("https://other.com", "https://example.com/", visited)

    def test_redirect_to_private_blocked(self):
        visited = set()
        with pytest.raises(RecoverableError):
            validate_redirect("https://example.com", "http://127 + .0.0.1", visited)

    def test_redirect_to_localhost_blocked(self):
        visited = set()
        with pytest.raises(RecoverableError):
            validate_redirect("https://example.com", "http://localhost/admin", visited)

    def test_redirect_to_file_blocked(self):
        visited = set()
        with pytest.raises(RecoverableError):
            validate_redirect("https://example.com", "file:///fake/passwd", visited)

    def test_valid_redirect_succeeds(self):
        visited = set()
        result = validate_redirect("https://example.com", "https://example.com/page2", visited)
        assert "example.com" in result
