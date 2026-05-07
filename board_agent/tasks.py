from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from .adapters.gpio import GpioAdapter
from .events import EventBus
from .models import TaskRecord, TaskRequest, TaskResponse


READ_ONLY_ACTIONS = {
    "demo": {"ping", "echo"},
    "gpio": {"read", "info"},
    "i2c": {"list"},
    "uart": {"list"},
    "rs232": {"list"},
    "rs485": {"list"},
    "can": {"status"},
    "pwm": {"list"},
    "adc": {"read", "list"},
}


@dataclass
class TaskManager:
    events: EventBus
    mock_mode: bool = False
    tasks: dict[str, TaskRecord] = field(default_factory=dict)

    def create(self, request: TaskRequest) -> TaskResponse:
        task_id = uuid.uuid4().hex[:12]
        record = TaskRecord(
            id=task_id,
            status="queued",
            message="Task queued",
            request=request,
        )
        rejection = self._validate(request)
        if rejection:
            record.status = "rejected"
            record.message = rejection
            self.tasks[task_id] = record
            return TaskResponse(id=task_id, status=record.status, message=record.message)

        self.tasks[task_id] = record
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            loop.create_task(self._run(record))
        return TaskResponse(id=task_id, status=record.status, message=record.message)

    def get(self, task_id: str) -> TaskRecord | None:
        return self.tasks.get(task_id)

    def _validate(self, request: TaskRequest) -> str | None:
        allowed = READ_ONLY_ACTIONS.get(request.interface, set())
        is_read_only = request.action in allowed
        if request.dry_run or self.mock_mode or is_read_only:
            return None
        if not request.confirm:
            return "Real hardware write actions require confirm=true"
        return None

    async def _run(self, record: TaskRecord) -> None:
        record.status = "running"
        record.message = "Task running"
        await self.events.publish("task.updated", record.model_dump())
        await self._log(record, "Task accepted")
        await asyncio.sleep(0.15)

        try:
            record.result = await asyncio.to_thread(self._dispatch, record.request)
            simulated = record.result.get("simulated", False)
            if simulated:
                await self._log(record, "Task ran in dry-run/mock mode")
            else:
                await self._log(record, "Task ran on hardware")
        except Exception as exc:
            record.status = "failed"
            record.message = str(exc)
            await self._log(record, record.message)
            await self.events.publish("task.updated", record.model_dump())
            return

        record.status = "completed"
        record.message = "Task completed"
        await self.events.publish("task.updated", record.model_dump())

    def _dispatch(self, request: TaskRequest) -> dict:
        if request.interface == "demo":
            return {
                "interface": request.interface,
                "action": request.action,
                "params": request.params,
                "simulated": True,
            }
        if request.interface == "gpio":
            return GpioAdapter(mock_mode=self.mock_mode).handle(
                request.action,
                request.params,
                dry_run=request.dry_run,
            )
        if request.dry_run or self.mock_mode:
            return {
                "interface": request.interface,
                "action": request.action,
                "params": request.params,
                "simulated": True,
                "note": "adapter pending",
            }
        raise RuntimeError(f"No hardware adapter implemented for {request.interface}")

    async def _log(self, record: TaskRecord, message: str) -> None:
        record.logs.append(message)
        await self.events.publish(
            "task.log",
            {"id": record.id, "message": message, "status": record.status},
        )
