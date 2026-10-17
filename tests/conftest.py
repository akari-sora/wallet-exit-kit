"""Offline tests. Outbound sockets may reach 127.0.0.1 only."""

import socket

import pytest

from tests.fake_rpc import serve


def _block_outbound(monkeypatch):
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("NO_PROXY", "*")
    real = socket.create_connection

    def guarded(address, *args, **kwargs):
        host = address[0]
        if host not in ("127.0.0.1", "::1", "localhost"):
            raise AssertionError("refusing outbound connection to " + str(host))
        return real(address, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", guarded)


_block_outbound = pytest.fixture(autouse=True)(_block_outbound)


def serve_rpc():
    servers = []

    def start(dispatch):
        httpd, url = serve(dispatch)
        servers.append(httpd)
        return url

    yield start
    for httpd in servers:
        httpd.shutdown()
        httpd.server_close()


serve_rpc = pytest.fixture(serve_rpc)
