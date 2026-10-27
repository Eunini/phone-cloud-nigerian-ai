import socket

import pytest

from scripts.resume_pinned_workspace import ReusablePortCheckSocket


def test_port_guard_allows_time_wait_but_never_displaces_a_live_listener():
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    address = listener.getsockname()
    listener.listen()
    try:
        with ReusablePortCheckSocket() as probe:
            with pytest.raises(OSError):
                probe.bind(address)
        with socket.create_connection(address) as client:
            connection, _ = listener.accept()
            connection.close()  # Server initiates close, leaving its port in TIME_WAIT.
            assert client.recv(1) == b""
    finally:
        listener.close()
    with ReusablePortCheckSocket() as probe:
        probe.bind(address)
