import sys
import types

import pytest

from board_agent.adapters.uart import UartAdapter


def test_uart_mock_list_returns_known_board_ports():
    adapter = UartAdapter(mock_mode=True)

    result = adapter.handle("list", {}, dry_run=True)

    assert result["ports"] == ["/dev/ttyS3", "/dev/ttyS7", "/dev/ttyS9"]
    assert result["simulated"] is True


def test_uart_dry_run_write_returns_payload_summary():
    adapter = UartAdapter(mock_mode=False)

    result = adapter.handle(
        "write",
        {"port": "/dev/ttyS3", "baudrate": 115200, "data": "AT", "line_ending": "crlf"},
        dry_run=True,
    )

    assert result["port"] == "/dev/ttyS3"
    assert result["bytes_written"] == 4
    assert result["hex"] == "41 54 0d 0a"
    assert result["simulated"] is True


def test_uart_rejects_invalid_port():
    adapter = UartAdapter(mock_mode=True)

    with pytest.raises(ValueError, match="port must look like"):
        adapter.handle("read", {"port": "/tmp/not-a-serial-port"}, dry_run=True)


def test_uart_rejects_invalid_hex_payload():
    adapter = UartAdapter(mock_mode=True)

    with pytest.raises(ValueError, match="complete hex bytes"):
        adapter.handle(
            "write",
            {"port": "/dev/ttyS3", "encoding": "hex", "data": "abc"},
            dry_run=True,
        )


def test_uart_real_transceive_uses_pyserial(monkeypatch):
    created = []

    class FakeSerial:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.written = b""
            created.append(self)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def write(self, data):
            self.written += data
            return len(data)

        def flush(self):
            return None

        def read(self, size):
            assert size == 8
            return b"OK\r\n"

    fake_serial_module = types.SimpleNamespace(Serial=FakeSerial)
    monkeypatch.setitem(sys.modules, "serial", fake_serial_module)

    adapter = UartAdapter(mock_mode=False)
    result = adapter.handle(
        "transceive",
        {
            "port": "/dev/ttyS3",
            "baudrate": 9600,
            "data": "AT",
            "line_ending": "crlf",
            "max_read_bytes": 8,
            "read_delay_ms": 0,
        },
        dry_run=False,
    )

    assert created[0].kwargs["port"] == "/dev/ttyS3"
    assert created[0].kwargs["baudrate"] == 9600
    assert created[0].written == b"AT\r\n"
    assert result["rx"] == "OK\r\n"
    assert result["bytes_read"] == 4
    assert result["simulated"] is False


def test_uart_real_listen_uses_longer_read_timeout(monkeypatch):
    created = []

    class FakeSerial:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            created.append(self)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size):
            assert size == 16
            return b"12345"

    fake_serial_module = types.SimpleNamespace(Serial=FakeSerial)
    monkeypatch.setitem(sys.modules, "serial", fake_serial_module)

    adapter = UartAdapter(mock_mode=False)
    result = adapter.handle(
        "listen",
        {
            "port": "/dev/ttyS3",
            "baudrate": 115200,
            "max_read_bytes": 16,
            "listen_timeout_ms": 5000,
        },
        dry_run=False,
    )

    assert created[0].kwargs["timeout"] == 5.0
    assert result["data"] == "12345"
    assert result["hex"] == "31 32 33 34 35"
    assert result["listen_timeout_ms"] == 5000
