import os
import socket
import struct
from typing import Optional
from urllib.parse import unquote, urlparse

from ._exceptions import WebSocketProxyException

__all__ = ["parse_url", "get_proxy_info"]


def parse_url(url: str) -> tuple:
    if ":" not in url:
        raise ValueError("url is invalid")

    scheme, url = url.split(":", 1)

    parsed = urlparse(url, scheme="http")
    if parsed.hostname:
        hostname = parsed.hostname
    else:
        raise ValueError("hostname is invalid")
    port = 0
    if parsed.port:
        port = parsed.port

    is_secure = False
    if scheme == "ws":
        if not port:
            port = 80
    elif scheme == "wss":
        is_secure = True
        if not port:
            port = 443
    else:
        raise ValueError("scheme %s is invalid" % scheme)

    if parsed.path:
        resource = parsed.path
    else:
        resource = "/"

    if parsed.query:
        resource += f"?{parsed.query}"

    return hostname, port, resource, is_secure


DEFAULT_NO_PROXY_HOST = ["localhost", "127.0.0.1"]


def _is_ip_address(addr: str) -> bool:
    try:
        socket.inet_aton(addr)
    except socket.error:
        return False
    else:
        return True


def _is_subnet_address(hostname: str) -> bool:
    try:
        addr, netmask = hostname.split("/")
        return _is_ip_address(addr) and 0 <= int(netmask) < 32
    except ValueError:
        return False


def _is_address_in_network(ip: str, net: str) -> bool:
    ipaddr: int = struct.unpack("!I", socket.inet_aton(ip))[0]
    netaddr, netmask = net.split("/")
    netaddr: int = struct.unpack("!I", socket.inet_aton(netaddr))[0]

    netmask = (0xFFFFFFFF << (32 - int(netmask))) & 0xFFFFFFFF
    return ipaddr & netmask == netaddr


def _is_no_proxy_host(hostname: str, no_proxy: Optional[list]) -> bool:
    if not no_proxy:
        if v := os.environ.get("no_proxy", os.environ.get("NO_PROXY", "")).replace(
        , ""
        ):
            no_proxy = v.split(",")
    if not no_proxy:
        no_proxy = DEFAULT_NO_PROXY_HOST

    if "*" in no_proxy:
        return True
    if hostname in no_proxy:
        return True
    if _is_ip_address(hostname):
        return any(
            [
                _is_address_in_network(hostname, subnet)
                for subnet in no_proxy
                if _is_subnet_address(subnet)
            ]
        )
    for domain in [domain for domain in no_proxy if domain.startswith(".")]:
        if hostname.endswith(domain):
            return True
    return False


def get_proxy_info(
        hostname: str,
        is_secure: bool,
        proxy_host: Optional[str] = None,
        proxy_port: int = 0,
        proxy_auth: Optional[tuple] = None,
        no_proxy: Optional[list] = None,
        proxy_type: str = "http",
) -> tuple:
    if _is_no_proxy_host(hostname, no_proxy):
        return None, 0, None

    if proxy_host:
        if not proxy_port:
            raise WebSocketProxyException("Cannot use port 0 when proxy_host specified")
        port = proxy_port
        auth = proxy_auth
        return proxy_host, port, auth

    env_key = "https_proxy" if is_secure else "http_proxy"
    value = os.environ.get(env_key, os.environ.get(env_key.upper(), "")).replace(
    , ""
    )
    if value:
        proxy = urlparse(value)
        auth = (
            (unquote(proxy.username), unquote(proxy.password))
            if proxy.username
            else None
        )
        return proxy.hostname, proxy.port, auth

    return None, 0, None
