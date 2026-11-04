import asyncio
import inspect
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from .discovery import get_discovered_task_by_name
from .exceptions import ZebrokNotImplementedError
from .logging import create_logger

logger = create_logger(__name__)


class BaseTaskRunner(ABC):
    """
    All task runners implementation must inherit from this base class
    """

    @abstractmethod
    def execute(self, task_name: str, *args: Any, **kwargs: Any) -> bool:
        """
        Abstract method for executing tasks

        Parameters:
            task_name (str): Name of task
        """
        raise ZebrokNotImplementedError


async def _await(awaitable: Awaitable[Any]) -> Any:
    return await awaitable


class DefaultTaskRunner(BaseTaskRunner):
    """
    Specialiazed task runner implementation
    for finding task in registry or through
    auto discovery feature and then executes it
    """

    def __init__(
        self,
        task_registry: Mapping[str, Callable[..., Any]],
        auto_discover: bool = False,
        max_retries: int = 0,
        retry_delay: float = 0.0,
    ) -> None:
        """
        parameters:
            task_registry: registry used to look tasks up by name
            auto_discover (bool): fall back to the tasks module when a task
                is not in the registry
            max_retries (int): extra attempts made when a task raises
            retry_delay (float): seconds to wait between attempts
        """
        if max_retries < 0:
            raise ValueError("max_retries must be zero or positive")
        if retry_delay < 0:
            raise ValueError("retry_delay must be zero or positive")
        self.auto_discover = auto_discover
        self.registry = task_registry
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def execute(self, task_name: str, *args: Any, **kwargs: Any) -> bool:
        """
        Executes the named task with the given arguments.

        Exceptions raised by the task are logged, never propagated, so one
        failing task can't take the worker down. Returns True if the task
        completed successfully.
        """
        func = self._find_task(task_name)
        if func is None:
            logger.error(f"Task not found: {task_name}")
            return False

        attempts = self.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                result = func(*args, **kwargs)
                if inspect.isawaitable(result):
                    asyncio.run(_await(result))
                return True
            except Exception:
                logger.exception(
                    f"Task '{task_name}' failed (attempt {attempt}/{attempts})",
                )
                if attempt < attempts and self.retry_delay:
                    time.sleep(self.retry_delay)
        return False

    def _find_task(self, task_name: str) -> Callable[..., Any] | None:
        """
        Looks the task up in the registry, then via auto discovery
        """
        func = self.registry.get(task_name)
        if func is None and self.auto_discover:
            func = get_discovered_task_by_name(task_name)
        return func
