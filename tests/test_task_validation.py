from board_agent.events import EventBus
from board_agent.models import TaskRequest
from board_agent.tasks import TaskManager


def test_write_task_without_confirm_is_rejected_when_not_dry_run():
    manager = TaskManager(events=EventBus(), mock_mode=False)
    response = manager.create(
        TaskRequest(
            interface="gpio",
            action="write",
            params={"chip": "/dev/gpiochip0", "line": 1, "value": 1},
            dry_run=False,
            confirm=False,
        )
    )

    assert response.status == "rejected"
    assert "confirm=true" in response.message


def test_dry_run_task_is_accepted_without_confirm():
    manager = TaskManager(events=EventBus(), mock_mode=False)
    response = manager.create(
        TaskRequest(
            interface="gpio",
            action="write",
            params={"chip": "/dev/gpiochip0", "line": 1, "value": 1},
            dry_run=True,
            confirm=False,
        )
    )

    assert response.status == "queued"


def test_confirmed_gpio_write_is_accepted():
    manager = TaskManager(events=EventBus(), mock_mode=False)
    response = manager.create(
        TaskRequest(
            interface="gpio",
            action="write",
            params={"chip": "/dev/gpiochip0", "line": 1, "value": 1, "duration_ms": 100},
            dry_run=False,
            confirm=True,
        )
    )

    assert response.status == "queued"
