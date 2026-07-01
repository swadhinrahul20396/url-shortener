"""Input validation for the URL shortener: scheme allowlist, SSRF blocklist,
length limits, and alias rules. Every rejection raises ValueError with a
specific, actionable reason -- callers should not need to guess why input
was rejected.
"""
import ipaddress
import re
import socket
from typing import Union
from urllib.parse import urlparse

# Only http/https may be shortened. Everything else (javascript:, data:,
# file:, ftp:, etc.) is a known vector for XSS or local-file/protocol abuse
# when the short link is later clicked.
ALLOWED_SCHEMES = {"http", "https"}

# Max total URL length. 2048 matches the de-facto limit most browsers/proxies
# tolerate; anything longer is rejected outright rather than truncated.
MAX_URL_LENGTH = 2048

MAX_ALIAS_LENGTH = 32
ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

# Aliases that would shadow real API routes if allowed as short codes.
RESERVED_ALIASES = {"api", "health", "docs", "openapi.json", "redoc", "static", "favicon.ico"}


def _is_blocked_ip(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    """Blocks loopback, private, link-local (incl. cloud metadata 169.254.169.254),
    and unspecified addresses -- the standard SSRF target ranges."""
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_unspecified
        or ip.is_reserved
    )


def validate_url(url: str) -> str:
    """Validate a candidate long URL. Returns the normalized URL string on
    success, raises ValueError with a specific reason on rejection."""
    if len(url) > MAX_URL_LENGTH:
        raise ValueError(f"URL exceeds maximum length of {MAX_URL_LENGTH} characters")

    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise ValueError(f"URL could not be parsed: {exc}") from exc

    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"scheme '{scheme or '(none)'}' is not allowed; use http or https"
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must include a hostname")

    # Resolve the hostname and block SSRF-prone targets. If the literal
    # hostname is already an IP, ipaddress.ip_address() parses it directly;
    # otherwise resolve via DNS so bare hostnames pointing at internal IPs
    # (e.g. "internal.corp" -> 10.0.0.5) are caught too.
    #
    # The IP-parse attempt and the SSRF check are kept in separate try
    # blocks deliberately: _check_ip_or_raise also raises ValueError, and if
    # it were inside the `except ValueError` scope for the parse attempt,
    # a blocked literal IP would be silently swallowed and fall through to
    # the DNS branch instead of being rejected.
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        _check_ip_or_raise(literal_ip)
    else:
        try:
            resolved = socket.getaddrinfo(hostname, None)
        except socket.gaierror as exc:
            raise ValueError(f"hostname '{hostname}' could not be resolved: {exc}") from exc
        for _family, _type, _proto, _canonname, sockaddr in resolved:
            _check_ip_or_raise(ipaddress.ip_address(sockaddr[0]))

    return url


def _check_ip_or_raise(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> None:
    if _is_blocked_ip(ip):
        raise ValueError(
            f"target address {ip} is a private/loopback/link-local address "
            "and cannot be shortened (SSRF protection)"
        )


def validate_alias(alias: str) -> str:
    """Validate a user-supplied custom short code."""
    if len(alias) > MAX_ALIAS_LENGTH:
        raise ValueError(f"alias exceeds maximum length of {MAX_ALIAS_LENGTH} characters")
    if not ALIAS_PATTERN.match(alias):
        raise ValueError("alias may only contain letters, numbers, hyphens, and underscores")
    if alias.lower() in RESERVED_ALIASES:
        raise ValueError(f"alias '{alias}' is reserved and cannot be used")
    return alias
