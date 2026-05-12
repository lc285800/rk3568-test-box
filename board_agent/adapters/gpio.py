from __future__ import annotations

import atexit
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Protocol


class CommandRunner(Protocol):
    def __call__(self, command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        ...


class ProcessStarter(Protocol):
    def __call__(self, command: list[str]) -> subprocess.Popen[str]:
        ...


@dataclass
class HeldOutput:
    process: subprocess.Popen[str]
    value: int


HELD_OUTPUTS: dict[tuple[str, int], HeldOutput] = {}


def default_runner(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def default_process_starter(command: list[str]) -> subprocess.Popen[str]:
    return subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


@dataclass(frozen=True)
class GpioAdapter:
    mock_mode: bool = False
    runner: CommandRunner = default_runner
    process_starter: ProcessStarter = default_process_starter

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
        held_values = {
            str(line): HELD_OUTPUTS[(chip, line)].value
            for line in lines
            if (chip, line) in HELD_OUTPUTS and HELD_OUTPUTS[(chip, line)].process.poll() is None
        }
        if held_values and len(held_values) == len(lines):
            return {
                "chip": chip,
                "values": held_values,
                "simulated": False,
                "source": "held_output",
            }
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
        active_low = bool(params.get("active_low", False))

        command = ["gpioset", "--mode=signal"]
        if active_low:
            command.append("--active-low")
        command.extend([chip, f"{line}={value}"])

        if dry_run or self.mock_mode:
            return {
                "chip": chip,
                "line": line,
                "value": value,
                "command": command,
                "simulated": True,
            }

        self._ensure_tool("gpioset")
        key = (chip, line)
        self._stop_held_output(key)
        process = self.process_starter(command)
        time.sleep(0.05)
        if process.poll() is not None:
            stderr = ""
            if process.stderr is not None:
                stderr = process.stderr.read().strip()
            raise RuntimeError(stderr or f"GPIO command exited early: {' '.join(command)}")
        HELD_OUTPUTS[key] = HeldOutput(process=process, value=value)
        return {
            "chip": chip,
            "line": line,
            "value": value,
            "mode": "held",
            "stdout": "",
            "simulated": False,
        }

    def _run(self, command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        tool = command[0]
        self._ensure_tool(tool)
        try:
            completed = self.runner(command, timeout)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"GPIO command timed out: {' '.join(command)}") from exc
        if completed.returncode != 0:
            output = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(output or f"GPIO command failed: {' '.join(command)}")
        return completed

    def _ensure_tool(self, tool: str) -> None:
        if shutil.which(tool) is None:
            raise RuntimeError(f"Required GPIO tool not found: {tool}")

    def _stop_held_output(self, key: tuple[str, int]) -> None:
        held = HELD_OUTPUTS.pop(key, None)
        if held is None or held.process.poll() is not None:
            return
        held.process.terminate()
        try:
            held.process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            held.process.kill()
            held.process.wait(timeout=1.0)


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


def stop_all_held_outputs() -> None:
    for key in list(HELD_OUTPUTS):
        held = HELD_OUTPUTS.pop(key)
        if held.process.poll() is None:
            held.process.terminate()


atexit.register(stop_all_held_outputs)
