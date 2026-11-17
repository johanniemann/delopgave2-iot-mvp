"""Trust one proxy service's overwritten client address, never arbitrary headers."""
from ipaddress import ip_address, IPv6Address
import socket

from starlette.requests import Request


def literal_address(value: str) -> str:
    if value != value.strip() or "%" in value:
        raise ValueError("A single unscoped IP literal is required.")
    address = ip_address(value)
    if isinstance(address, IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return str(address)


def socket_peer(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    try:
        return literal_address(peer)
    except ValueError:
        return peer


def resolve_client_identity(request: Request, trusted_proxy_host: str) -> str:
    peer = socket_peer(request)
    values = request.headers.getlist("x-real-ip")
    if not trusted_proxy_host or len(values) != 1:
        return peer
    try:
        client = literal_address(values[0])
        # A new Docker service address revokes trust in its previous address.
        # Request-time discovery also avoids the app/Caddy startup dependency.
        addresses = {literal_address(result[4][0]) for result in socket.getaddrinfo(
            trusted_proxy_host, None, type=socket.SOCK_STREAM)}
    except (OSError, ValueError):
        return peer
    return client if peer in addresses else peer
