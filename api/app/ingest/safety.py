"""Guards for user-supplied URLs when strangers can reach the API (PUBLIC_MODE=1).

Off by default so the local demo can audit localhost:4100 and local directories.
"""

import asyncio
import ipaddress
import os
import socket
from urllib.parse import urlparse

_LOCAL_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home.arpa")


class UnsafeURL(ValueError):
    pass


def public_mode() -> bool:
    return os.getenv("PUBLIC_MODE", "").strip().lower() in {"1", "true", "yes"}


def _blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return not ip.is_global or ip.is_multicast


async def _resolve(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [info[4][0].split("%")[0] for info in infos]


def literal_local(url: str) -> bool:
    """True for URLs whose host is a private/loopback IP literal or a local-only name (no DNS lookup)."""
    host = (urlparse(url).hostname or "").lower()
    if host == "localhost" or host.endswith(_LOCAL_SUFFIXES):
        return True
    try:
        return _blocked(ipaddress.ip_address(host))
    except ValueError:
        return False


async def check_url(url: str) -> None:
    """Raise UnsafeURL in public mode unless `url` is http(s) and every address it resolves to is public."""
    if not public_mode():
        return
    parsed = urlparse(url)
    host = parsed.hostname
    if parsed.scheme not in ("http", "https") or not host:
        raise UnsafeURL("only http(s) URLs are accepted")
    if literal_local(url):
        raise UnsafeURL(f"{host} is a private or local address")
    try:
        ipaddress.ip_address(host)
        return  # a public IP literal
    except ValueError:
        pass
    try:
        addrs = await _resolve(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except OSError:
        raise UnsafeURL(f"cannot resolve {host}") from None
    if not addrs or any(_blocked(ipaddress.ip_address(a)) for a in addrs):
        raise UnsafeURL(f"{host} resolves to a private or local address")


def check_local_path() -> None:
    if public_mode():
        raise UnsafeURL("local paths are not accepted; give a public URL")
