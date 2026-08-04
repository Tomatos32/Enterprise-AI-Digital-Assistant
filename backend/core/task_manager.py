"""Active Task Registry for Managing and Cancelling Asynchronous Chat Tasks."""

import asyncio
from typing import Dict, Optional


class TaskManager:
    """
    In-memory registry tracking running asyncio.Tasks by thread_id.
    Enables layer-2 task cancellation when a user requests an AI generation abort.
    """

    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}

    def register_task(self, thread_id: str, task: asyncio.Task):
        """Registers a running asyncio Task for a given thread_id."""
        self._tasks[thread_id] = task

    def unregister_task(self, thread_id: str):
        """Removes a task from registry upon completion."""
        self._tasks.pop(thread_id, None)

    def abort_task(self, thread_id: str) -> bool:
        """
        Cancels the active task for thread_id if running.
        Returns True if a task was found and cancelled, False otherwise.
        """
        task = self._tasks.get(thread_id)
        if task and not task.done():
            task.cancel()
            self._tasks.pop(thread_id, None)
            return True
        return False

    def get_task(self, thread_id: str) -> Optional[asyncio.Task]:
        """Retrieves active task for thread_id."""
        return self._tasks.get(thread_id)


# Singleton instance
task_manager = TaskManager()
