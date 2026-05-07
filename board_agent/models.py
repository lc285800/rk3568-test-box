from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    mode: str


class SystemInfo(BaseModel):
    hostname: str
    kernel: str
    os: str
    arch: str
    cpu: str
    memory_total: str
    network: list[str]


class Resources(BaseModel):
    gpiochips: list[str] = Field(default_factory=list)
    i2c_buses: list[str] = Field(default_factory=list)
    serial_ports: list[str] = Field(default_factory=list)
    can_interfaces: list[str] = Field(default_factory=list)
    pwm_chips: list[str] = Field(default_factory=list)
    adc_channels: list[str] = Field(default_factory=list)
    tools: dict[str, bool] = Field(default_factory=dict)
    mode: str


class TaskRequest(BaseModel):
    interface: Literal["gpio", "i2c", "uart", "rs232", "rs485", "can", "pwm", "adc", "demo"]
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    confirm: bool = False
    dry_run: bool = True


class TaskResponse(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed", "rejected"]
    message: str


class TaskRecord(TaskResponse):
    request: TaskRequest
    logs: list[str] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
