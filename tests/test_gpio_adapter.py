import subprocess

import pytest

from board_agent.adapters.gpio import GpioAdapter, HELD_OUTPUTS


def test_gpio_mock_read_returns_values():
    adapter = GpioAdapter(mock_mode=True)

    result = adapter.handle(
        "read",
        {"chip": "/dev/gpiochip0", "lines": [0, 1]},
        dry_run=True,
    )

    assert result["values"] == {"0": 0, "1": 1}
    assert result["simulated"] is True


def test_gpio_mock_write_builds_held_gpioset_command():
    adapter = GpioAdapter(mock_mode=True)

    result = adapter.handle(
        "write",
        {"chip": "/dev/gpiochip0", "line": 3, "value": 1},
        dry_run=True,
    )

    assert result["command"] == [
        "gpioset",
        "--mode=signal",
        "/dev/gpiochip0",
        "3=1",
    ]


def test_gpio_rejects_invalid_line():
    adapter = GpioAdapter(mock_mode=True)

    with pytest.raises(ValueError, match="between 0 and 511"):
        adapter.handle("read", {"chip": "/dev/gpiochip0", "line": 999}, dry_run=True)


def test_gpio_real_read_parses_command_output(monkeypatch):
    commands = []

    def fake_runner(command, timeout):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="1 0\n", stderr="")

    monkeypatch.setattr("board_agent.adapters.gpio.shutil.which", lambda tool: f"/usr/bin/{tool}")
    adapter = GpioAdapter(mock_mode=False, runner=fake_runner)

    result = adapter.handle(
        "read",
        {"chip": "/dev/gpiochip0", "lines": [4, 5]},
        dry_run=False,
    )

    assert commands == [["gpioget", "/dev/gpiochip0", "4", "5"]]
    assert result["values"] == {"4": 1, "5": 0}
    assert result["simulated"] is False


class FakeProcess:
    def __init__(self):
        self.terminated = False
        self.killed = False
        self.stderr = None

    def poll(self):
        return None

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        return 0


def test_gpio_real_write_holds_output_and_replaces_previous(monkeypatch):
    commands = []
    processes = []

    def fake_process_starter(command):
        commands.append(command)
        process = FakeProcess()
        processes.append(process)
        return process

    HELD_OUTPUTS.clear()
    monkeypatch.setattr("board_agent.adapters.gpio.shutil.which", lambda tool: f"/usr/bin/{tool}")
    adapter = GpioAdapter(mock_mode=False, process_starter=fake_process_starter)

    first = adapter.handle(
        "write",
        {"chip": "/dev/gpiochip0", "line": 3, "value": 1},
        dry_run=False,
    )
    second = adapter.handle(
        "write",
        {"chip": "/dev/gpiochip0", "line": 3, "value": 0},
        dry_run=False,
    )

    assert first["mode"] == "held"
    assert second["mode"] == "held"
    assert commands == [
        ["gpioset", "--mode=signal", "/dev/gpiochip0", "3=1"],
        ["gpioset", "--mode=signal", "/dev/gpiochip0", "3=0"],
    ]
    assert processes[0].terminated is True
    assert HELD_OUTPUTS[("/dev/gpiochip0", 3)].value == 0
    HELD_OUTPUTS.clear()
