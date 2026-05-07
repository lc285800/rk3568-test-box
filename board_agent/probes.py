from __future__ import annotations

import glob
import os
import platform
import shutil
import socket
import subprocess
from pathlib import Path

from .models import Resources, SystemInfo


TOOLS = [
    "gpiodetect",
    "gpioinfo",
    "gpioget",
    "gpioset",
    "i2cdetect",
    "i2cget",
    "i2cset",
    "candump",
    "cansend",
    "ip",
    "stty",
]


def run_text(command: list[str], timeout: float = 2.0) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return (completed.stdout or completed.stderr).strip()


def list_glob(pattern: str) -> list[str]:
    return sorted(glob.glob(pattern))


def get_system_info(mock: bool = False) -> SystemInfo:
    if mock:
        return SystemInfo(
            hostname="rk3568-mock",
            kernel="Linux 4.19.232",
            os="Ubuntu 20.04.6 LTS",
            arch="aarch64",
            cpu="4 x Cortex-A55",
            memory_total="3.8 GiB",
            network=["eth0 192.168.2.88/24", "can0 DOWN", "can1 DOWN"],
        )

    os_release = Path("/etc/os-release")
    pretty_os = "unknown"
    if os_release.exists():
        for line in os_release.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("PRETTY_NAME="):
                pretty_os = line.split("=", 1)[1].strip('"')
                break

    meminfo = Path("/proc/meminfo")
    memory_total = "unknown"
    if meminfo.exists():
        first = meminfo.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
        memory_total = first.replace("MemTotal:", "").strip()

    network_text = run_text(["ip", "-br", "addr"])
    network = [line for line in network_text.splitlines() if line.strip()]

    cpu = platform.processor() or platform.machine()
    return SystemInfo(
        hostname=socket.gethostname(),
        kernel=f"{platform.system()} {platform.release()}",
        os=pretty_os,
        arch=platform.machine(),
        cpu=cpu,
        memory_total=memory_total,
        network=network,
    )


def get_resources(mock: bool = False) -> Resources:
    if mock:
        return Resources(
            gpiochips=[f"/dev/gpiochip{i}" for i in range(6)],
            i2c_buses=["/dev/i2c-0", "/dev/i2c-5", "/dev/i2c-6"],
            serial_ports=["/dev/ttyS3", "/dev/ttyS7", "/dev/ttyS9"],
            can_interfaces=["can0", "can1"],
            pwm_chips=["/sys/class/pwm/pwmchip0"],
            adc_channels=["/sys/bus/iio/devices/iio:device0/in_voltage0_raw"],
            tools={tool: True for tool in TOOLS},
            mode="mock",
        )

    can_interfaces = []
    net_class = Path("/sys/class/net")
    if net_class.exists():
        can_interfaces = sorted(
            item.name for item in net_class.iterdir() if item.name.startswith("can")
        )

    adc_channels = sorted(
        str(path)
        for path in Path("/sys/bus/iio/devices").glob("iio:device*/in_voltage*_raw")
    )

    return Resources(
        gpiochips=list_glob("/dev/gpiochip*"),
        i2c_buses=list_glob("/dev/i2c-*"),
        serial_ports=sorted(
            set(list_glob("/dev/ttyS*") + list_glob("/dev/ttyUSB*") + list_glob("/dev/ttyCH*"))
        ),
        can_interfaces=can_interfaces,
        pwm_chips=sorted(str(path) for path in Path("/sys/class/pwm").glob("pwmchip*")),
        adc_channels=adc_channels,
        tools={tool: shutil.which(tool) is not None for tool in TOOLS},
        mode=os.getenv("RK_BOX_MODE", "auto"),
    )
