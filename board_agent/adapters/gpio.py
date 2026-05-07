from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol


class CommandRunner(Protocol):
    def __call__(self, command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        ...


def default_runner(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@dataclass(frozen=True)
class GpioAdapter:
    mock_mode: bool = False
    runner: CommandRunner = default_runner

    def handle(self, action: str, params: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        if action == "info":
            return self.info(params)
        if action == "read":
            return self.read(params)
        if action == "write":
            return self.write(params, dry_run=dry_run)
        raise ValueError(f"Unsupported GPIO action: {action}")

    def info(self, params: dict[str, Any]) -> dict[str, Any]:
        chip = optional_chip(params.get("chip"))
        if self.mock_mode:
            return {
                "chip": chip or "all",
                "text": mock_gpioinfo(chip),
                "simulated": True,
            }

        command = ["gpioinfo"]
        if chip:
            command.append(chip)
        completed = self._run(command, timeout=3.0)
        return {"chip": chip or "all", "text": completed.stdout.strip(), "simulated": False}

    def read(self, params: dict[str, Any]) -> dict[str, Any]:
        chip = require_chip(params.get("chip"))
        lines = parse_lines(params)
        active_low = bool(params.get("active_low", False))
        if self.mock_mode:
            values = {str(line): line % 2 for line in lines}
            return {"chip": chip, "values": values, "simulated": True}

        command = ["gpioget"]
        if active_low:
            command.append("--active-low")
        command.extend([chip, *[str(line) for line in lines]])
        completed = self._run(command, timeout=2.0)
        raw_values = completed.stdout.strip().split()
        values = {str(line): int(raw_values[index]) for index, line in enumerate(lines)}
        return {"chip": chip, "values": values, "simulated": False}

    def write(self, params: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        chip = require_chip(params.get("chip"))
        line = parse_line(params.get("line"))
        value = parse_value(params.get("value"))
        duration_ms = parse_duration_ms(params.get("duration_ms", 200))
        active_low = bool(params.get("active_low", False))

        command = ["gpioset", "--mode=time"]
        if active_low:
            command.append("--active-low")
        seconds, usec = divmod(duration_ms * 1000, 1_000_000)
        if seconds:
            command.append(f"--sec={seconds}")
        if usec:
            command.append(f"--usec={usec}")
        command.extend([chip, f"{line}={value}"])

        if dry_run or self.mock_mode:
            return {
                "chip": chip,
                "line": line,
                "value": value,
                "duration_ms": duration_ms,
                "command": command,
                "simulated": True,
            }

        completed = self._run(command, timeout=max(2.0, duration_ms / 1000 + 2.0))
        return {
            "chip": chip,
            "line": line,
            "value": value,
            "duration_ms": duration_ms,
            "stdout": completed.stdout.strip(),
            "simulated": False,
        }

    def _run(self, command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        tool = command[0]
        if shutil.which(tool) is None:
            raise RuntimeError(f"Required GPIO tool not found: {tool}")
        try:
            completed = self.runner(command, timeout)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"GPIO command timed out: {' '.join(command)}") from exc
        if completed.returncode != 0:
            output = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(output or f"GPIO command failed: {' '.join(command)}")
        return completed


def optional_chip(value: Any) -> str | None:
    if value in (None, ""):
        return None
    chip = str(value)
    if not re.fullmatch(r"(/dev/)?gpiochip[0-9]+|gpiochip[0-9]+|[0-9]+", chip):
        raise ValueError("GPIO chip must look like /dev/gpiochip0, gpiochip0, or 0")
    return chip


def require_chip(value: Any) -> str:
    chip = optional_chip(value)
    if chip is None:
        raise ValueError("GPIO chip is required")
    return chip


def parse_lines(params: dict[str, Any]) -> list[int]:
    if "lines" in params:
        raw_lines = params["lines"]
        if not isinstance(raw_lines, list) or not raw_lines:
            raise ValueError("GPIO lines must be a non-empty list")
        return [parse_line(item) for item in raw_lines]
    return [parse_line(params.get("line"))]


def parse_line(value: Any) -> int:
    if value is None or value == "":
        raise ValueError("GPIO line is required")
    try:
        line = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("GPIO line must be an integer") from exc
    if not 0 <= line <= 511:
        raise ValueError("GPIO line must be between 0 and 511")
    return line


def parse_value(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("GPIO value must be 0 or 1") from exc
    if parsed not in (0, 1):
        raise ValueError("GPIO value must be 0 or 1")
    return parsed


def parse_duration_ms(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("GPIO duration_ms must be an integer") from exc
    if not 10 <= parsed <= 10_000:
        raise ValueError("GPIO duration_ms must be between 10 and 10000")
    return parsed


def mock_gpioinfo(chip: str | None) -> str:
    chip_name = chip or "gpiochip0"
    return "\n".join(
        [
            f"{chip_name} - 32 lines:",
            '    line   0:      unnamed       unused   input  active-high',
            '    line   1:      unnamed       unused   input  active-high',
            '    line   2:      unnamed       unused   output active-high',
        ]
    )
