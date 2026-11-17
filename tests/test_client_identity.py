"""Literal parsing and Docker service lifecycle at the only proxy trust boundary."""
import socket

import pytest
from starlette.requests import Request

from app.client_identity import resolve_client_identity
from app.main import Settings


PROXY = "172.29.0.8"


def request(values, peer=PROXY):
    return Request({"type": "http", "client": (peer, 1234), "headers": [
        (b"x-real-ip", value.encode()) for value in values]})


def discovered(monkeypatch, address=PROXY):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 0))])


@pytest.mark.parametrize("values", [[], [""], [" "], ["198.51.100.1 "],
    ["198.51.100.1", "198.51.100.1"], ["198.51.100.1", "198.51.100.2"],
    ["198.51.100.1, 198.51.100.2"], ["198.51.100.1:443"], ["[2001:db8::1]"],
    ["fe80::1%eth0"], ["client.example"], ["010.000.000.001"]])
def test_invalid_or_ambiguous_header_falls_back_to_actual_peer(monkeypatch, values):
    discovered(monkeypatch)
    assert resolve_client_identity(request(values), "caddy") == PROXY


@pytest.mark.parametrize("value, expected", [("198.51.100.1", "198.51.100.1"),
    ("2001:DB8:0:0:0:0:0:1", "2001:db8::1"), ("::ffff:198.51.100.1", "198.51.100.1")])
def test_trusted_peer_accepts_and_canonicalizes_one_ip(monkeypatch, value, expected):
    discovered(monkeypatch)
    assert resolve_client_identity(request([value]), "caddy") == expected


def test_fresh_discovery_handles_failure_then_proxy_recreation(monkeypatch):
    def unavailable(*args, **kwargs):
        raise socket.gaierror("internal DNS temporarily unavailable")

    monkeypatch.setattr(socket, "getaddrinfo", unavailable)
    assert resolve_client_identity(request(["198.51.100.1"]), "caddy") == PROXY
    discovered(monkeypatch)
    assert resolve_client_identity(request(["198.51.100.1"]), "caddy") == "198.51.100.1"
    discovered(monkeypatch, "172.29.0.9")
    assert resolve_client_identity(request(["198.51.100.1"]), "caddy") == PROXY
    assert resolve_client_identity(request(["198.51.100.1"], peer="172.29.0.9"), "caddy") == "198.51.100.1"


def test_default_local_mode_does_not_consult_dns_or_trust_headers(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unconfigured proxy trust must not consult DNS")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    assert resolve_client_identity(request(["198.51.100.1"]), "") == PROXY
    assert resolve_client_identity(Request({"type": "http", "headers": []}), "caddy") == "unknown"


def test_proxy_trust_requires_explicit_shared_configuration(monkeypatch):
    with pytest.raises(ValueError, match="TRUSTED_PROXY_HOST"):
        Settings(database_url="unused", trusted_proxy_host="caddy")
    monkeypatch.setenv("DATABASE_URL", "unused")
    monkeypatch.setenv("APP_MODE", "shared")
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://example.test")
    monkeypatch.setenv("TRUSTED_PROXY_HOST", "caddy")
    assert Settings.from_env().trusted_proxy_host == "caddy"
