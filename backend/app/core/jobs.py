"""
In-process background job runner.

Keeps strong references to tasks (so they aren't garbage collected), logs
failures and cancels everything on shutdown. Replace with ARQ/Celery when
generation must survive restarts or scale across machines.
"""

import asyncio
from collections.abc import Coroutine
from typing import Any

from loguru import logger


class JobRunner:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task] = set()

    def submit(self, coro: Coroutine[Any, Any, Any], name: str = "job") -> asyncio.Task:
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._done)
        return task

    def _done(self, task: asyncio.Task) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and task.exception():
            logger.error(f"Background job {task.get_name()} failed: {task.exception()!r}")

    async def wait_all(self, timeout: float = 30) -> None:
        if self._tasks:
            await asyncio.wait(list(self._tasks), timeout=timeout)

    async def shutdown(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    @property
    def active(self) -> int:
        return len(self._tasks)
