"""Keep the default suite offline and isolate its implicit backend database."""
import ipaddress
import socket
import tempfile
from pathlib import Path

import pytest


def _loopback(host):
    if host is None:  # getaddrinfo(None, ...) is used to bind local servers.
        return True
    if isinstance(host, bytes):
        try:
            host = host.decode("ascii")
        except UnicodeError:
            return False
    if isinstance(host, str) and host.lower().rstrip(".") == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        return False


def pytest_configure(config):
    """Install before test-module imports, which can instantiate backend.main."""
    patcher = pytest.MonkeyPatch()
    temporary = tempfile.TemporaryDirectory(prefix="collection-engine-tests-")
    config._collection_engine_test_environment = (patcher, temporary)
    patcher.setenv("SHOPPING_DB_PATH", str(Path(temporary.name) / "products.db"))
    patcher.setenv("PYTHON_DOTENV_DISABLED", "1")
    from collection_engine.registry import policies
    for policy in policies().values():
        for key in policy.credential_env:
            patcher.delenv(key, raising=False)
    original_lookup = socket.getaddrinfo
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def deny():
        raise RuntimeError("External network is disabled in tests; mock provider responses")

    def lookup(host, *args, **kwargs):
        if not _loopback(host):
            deny()
        return original_lookup(host, *args, **kwargs)

    def connect(connection, address):
        if connection.family in (socket.AF_INET, socket.AF_INET6) and not _loopback(address[0]):
            deny()
        return original_connect(connection, address)

    def connect_ex(connection, address):
        if connection.family in (socket.AF_INET, socket.AF_INET6) and not _loopback(address[0]):
            deny()
        return original_connect_ex(connection, address)

    patcher.setattr(socket, "getaddrinfo", lookup)
    patcher.setattr(socket.socket, "connect", connect)
    patcher.setattr(socket.socket, "connect_ex", connect_ex)


def pytest_unconfigure(config):
    environment = getattr(config, "_collection_engine_test_environment", None)
    if environment:
        patcher, temporary = environment
        patcher.undo()
        temporary.cleanup()
