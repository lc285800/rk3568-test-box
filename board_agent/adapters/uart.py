from __future__ import annotations

import glob
import re
import time
from dataclasses import dataclass
from typing import Any


BAUD_RATES = {
    1200,
    2400,
    4800,
    9600,
    19200,
    38400,
    57600,
    115200,
    230400,
    460800,
    921600,
}
DATA_BITS = {5, 6, 7, 8}
STOP_BITS = {1, 2}
PARITIES = {"N", "E", "O"}


@dataclass(frozen=True)
class UartAdapter:
    mock_mode: bool = False

    def handle(self, action: str, params: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        if action == "list":
            return self.list_ports()
        if action == "read":
            return self.read(params)
        if action == "listen":
            return self.listen(params)
        if action == "write":
            return self.write(params, dry_run=dry_run)
        if action == "transceive":
            return self.transceive(params, dry_run=dry_run)
        raise ValueError(f"Unsupported UART action: {action}")

    def list_ports(self) -> dict[str, Any]:
        if self.mock_mode:
            return {
                "ports": ["/dev/ttyS3", "/dev/ttyS7", "/dev/ttyS9"],
                "simulated": True,
            }
        ports = sorted(
            set(
                glob.glob("/dev/ttyS*")
                + glob.glob("/dev/ttyUSB*")
                + glob.glob("/dev/ttyAMA*")
                + glob.glob("/dev/ttyCH*")
            )
        )
        return {"ports": ports, "simulated": False}

    def read(self, params: dict[str, Any]) -> dict[str, Any]:
        config = parse_uart_config(params)
        read_timeout = parse_timeout(params.get("read_timeout_ms", 500), "read_timeout_ms")
        if self.mock_mode:
            return {
                **config.public(),
                "data": "",
                "encoding": "text",
                "bytes_read": 0,
                "simulated": True,
            }

        serial = import_serial()
        with serial.Serial(**config.pyserial_kwargs(timeout=read_timeout)) as port:
            data = port.read(config.max_read_bytes)
        return {
            **config.public(),
            "data": data.decode("utf-8", errors="replace"),
            "hex": data.hex(" "),
            "bytes_read": len(data),
            "simulated": False,
        }

    def listen(self, params: dict[str, Any]) -> dict[str, Any]:
        listen_timeout_ms = parse_non_negative_int(
            params.get("listen_timeout_ms", 5000),
            "listen_timeout_ms",
            100,
            60000,
        )
        listen_params = {**params, "read_timeout_ms": listen_timeout_ms}
        result = self.read(listen_params)
        result["listen_timeout_ms"] = listen_timeout_ms
        return result

    def write(self, params: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        config = parse_uart_config(params)
        payload = parse_payload(params)
        if dry_run or self.mock_mode:
            return {
                **config.public(),
                "data": payload.preview_text,
                "hex": payload.data.hex(" "),
                "bytes_written": len(payload.data),
                "simulated": True,
            }

        serial = import_serial()
        with serial.Serial(**config.pyserial_kwargs(timeout=config.timeout_s)) as port:
            written = port.write(payload.data)
            port.flush()
        return {
            **config.public(),
            "bytes_written": written,
            "simulated": False,
        }

    def transceive(self, params: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        config = parse_uart_config(params)
        payload = parse_payload(params)
        read_timeout = parse_timeout(params.get("read_timeout_ms", 500), "read_timeout_ms")
        delay_ms = parse_non_negative_int(params.get("read_delay_ms", 20), "read_delay_ms", 0, 10000)
        if dry_run or self.mock_mode:
            response = payload.data if self.mock_mode else b""
            return {
                **config.public(),
                "tx": payload.preview_text,
                "tx_hex": payload.data.hex(" "),
                "rx": response.decode("utf-8", errors="replace"),
                "rx_hex": response.hex(" "),
                "bytes_written": len(payload.data),
                "bytes_read": len(response),
                "simulated": True,
            }

        serial = import_serial()
        with serial.Serial(**config.pyserial_kwargs(timeout=read_timeout)) as port:
            written = port.write(payload.data)
            port.flush()
            time.sleep(delay_ms / 1000)
            response = port.read(config.max_read_bytes)
        return {
            **config.public(),
            "tx": payload.preview_text,
            "tx_hex": payload.data.hex(" "),
            "rx": response.decode("utf-8", errors="replace"),
            "rx_hex": response.hex(" "),
            "bytes_written": written,
            "bytes_read": len(response),
            "simulated": False,
        }


@dataclass(frozen=True)
class UartConfig:
    port: str
    baudrate: int
    bytesize: int
    parity: str
    stopbits: int
    timeout_s: float
    max_read_bytes: int

    def pyserial_kwargs(self, timeout: float) -> dict[str, Any]:
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "bytesize": self.bytesize,
            "parity": self.parity,
            "stopbits": self.stopbits,
            "timeout": timeout,
            "write_timeout": self.timeout_s,
        }

    def public(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "bytesize": self.bytesize,
            "parity": self.parity,
            "stopbits": self.stopbits,
            "timeout_ms": int(self.timeout_s * 1000),
            "max_read_bytes": self.max_read_bytes,
        }


@dataclass(frozen=True)
class Payload:
    data: bytes
    preview_text: str


def parse_uart_config(params: dict[str, Any]) -> UartConfig:
    port = require_port(params.get("port"))
    return UartConfig(
        port=port,
        baudrate=parse_choice_int(params.get("baudrate", 115200), "baudrate", BAUD_RATES),
        bytesize=parse_choice_int(params.get("bytesize", 8), "bytesize", DATA_BITS),
        parity=parse_parity(params.get("parity", "N")),
        stopbits=parse_choice_int(params.get("stopbits", 1), "stopbits", STOP_BITS),
        timeout_s=parse_timeout(params.get("timeout_ms", 1000), "timeout_ms"),
        max_read_bytes=parse_non_negative_int(
            params.get("max_read_bytes", 256),
            "max_read_bytes",
            1,
            4096,
        ),
    )


def require_port(value: Any) -> str:
    if value in (None, ""):
        raise ValueError("UART port is required")
    port = str(value)
    if not re.fullmatch(r"/dev/tty(S|USB|AMA|CH)[A-Za-z0-9]+", port):
        raise ValueError("UART port must look like /dev/ttyS3 or /dev/ttyUSB0")
    return port


def parse_choice_int(value: Any, name: str, allowed: set[int]) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"UART {name} must be an integer") from exc
    if parsed not in allowed:
        allowed_text = ", ".join(str(item) for item in sorted(allowed))
        raise ValueError(f"UART {name} must be one of: {allowed_text}")
    return parsed


def parse_parity(value: Any) -> str:
    parity = str(value or "N").upper()
    if parity not in PARITIES:
        raise ValueError("UART parity must be N, E, or O")
    return parity


def parse_timeout(value: Any, name: str) -> float:
    return parse_non_negative_int(value, name, 1, 60000) / 1000


def parse_non_negative_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"UART {name} must be an integer") from exc
    if not minimum <= parsed <= maximum:
        raise ValueError(f"UART {name} must be between {minimum} and {maximum}")
    return parsed


def parse_payload(params: dict[str, Any]) -> Payload:
    encoding = str(params.get("encoding", "text")).lower()
    if encoding == "hex":
        raw = str(params.get("data", "")).replace(" ", "")
        if not raw:
            raise ValueError("UART hex data is required")
        if len(raw) % 2 != 0 or not re.fullmatch(r"[0-9a-fA-F]+", raw):
            raise ValueError("UART hex data must contain complete hex bytes")
        data = bytes.fromhex(raw)
        return Payload(data=data, preview_text=data.decode("utf-8", errors="replace"))

    if encoding != "text":
        raise ValueError("UART encoding must be text or hex")
    text = str(params.get("data", ""))
    line_ending = str(params.get("line_ending", "none")).lower()
    endings = {"none": "", "lf": "\n", "cr": "\r", "crlf": "\r\n"}
    if line_ending not in endings:
        raise ValueError("UART line_ending must be none, lf, cr, or crlf")
    data = f"{text}{endings[line_ending]}".encode("utf-8")
    if not data:
        raise ValueError("UART data is required")
    return Payload(data=data, preview_text=text)


def import_serial():
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError("pyserial is required for UART hardware access") from exc
    return serial
