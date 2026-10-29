"""A suíte comum é offline; PostgreSQL real usa seu executor dedicado."""

import socket
from typing import NoReturn

import pytest


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch: pytest.MonkeyPatch) -> None:
    original_connect = socket.socket.connect
    original_resolve = socket.getaddrinfo
    loopback = ("127.0.0.1", "::1", "localhost", b"localhost")

    def blocked(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError(
            "Rede bloqueada na suíte offline: use fixtures ou transporte simulado."
        )

    def connect(sock, address):
        # asyncio.socketpair usa TCP loopback no Windows; não é consulta à fonte.
        if isinstance(address, tuple) and address[0] in loopback:
            return original_connect(sock, address)
        return blocked()

    def resolve(host, *args, **kwargs):
        if host in loopback:
            return original_resolve(host, *args, **kwargs)
        return blocked()

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "getaddrinfo", resolve)
