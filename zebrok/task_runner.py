from abc import ABC
from abc import abstractmethod

from .discovery import get_discovered_task_by_name
from .exceptions import ZebrokNotImplementedError
from .logging import create_logger

from typing import Dict

logger = create_logger(__name__)


class BaseTaskRunner(ABC):
    """
    All task runners implementation must inherit from this base class
    """

    @abstractmethod
    def execute(self, task_name: str, **kwargs: Dict) -> bool:
        """
        Abstract method for executing tasks

        Parameters:
            task_name (str): Name of task
        """
        raise ZebrokNotImplementedError


class DefaultTaskRunner(BaseTaskRunner):
    """
    Specialiazed task runner implementation
    for finding task in registry or through
    auto discovery feature and then executes it
    """

    def __init__(self, task_registry, auto_discover=False) -> None:
        self.auto_discover = auto_discover
        self.registry = task_registry

    def execute(self, task_name: str, **kwargs: Dict) -> bool:
        """
        Executes provided task name with provided keyword
        arguments
        """
        return self._find_and_execute_task(task_name, **kwargs)

    def _find_and_execute_task(self, task_name: str, **kwargs: Dict) -> bool:
        """
        Finds and execute tasks
        """
        task_executed = False
        func = self.registry.get(task_name)

        if not func and self.auto_discover:
            func = get_discovered_task_by_name(task_name)

        if func:
            func(**kwargs)
            task_executed = True
        else:
            logger.error("Task not found!")

        return task_executed
