import inspect
from abc import ABC, abstractmethod
from typing import Any

from .app import Task
from .exceptions import ZebrokNotImplementedError


class BaseTaskRegistry(ABC):
    """
    Concrete task registry types must
    inherit this abstract class
    """

    @abstractmethod
    def register(self, task: Task) -> None:
        """
        Add a new task to the registry

        parameters:
            task (object): the function to be added to the registry
        """
        raise ZebrokNotImplementedError

    @abstractmethod
    def unregister(self, name: str) -> None:
        """
        Remove a task to the registry

        parameters:
            name (object): name of function to be remove from the registry
        """
        raise ZebrokNotImplementedError


class InMemoryTaskRegistry(BaseTaskRegistry, dict):
    """
    In-memory implementation of Task registry
    """

    def register(self, task: Any) -> None:
        """
        Adds a task to in-memory registry. Accepts a Task, a Task subclass,
        or a plain function (which is wrapped in a Task).
        """
        if inspect.isclass(task):
            task = task()
        if not isinstance(task, Task):
            task = Task(task)
        self[task.name] = task

    def unregister(self, name: Any) -> None:
        """
        Removes a task from in-memory registry, by name or by Task object
        """
        self.pop(name.name if isinstance(name, Task) else name)


class RegistryType:
    """
    RegistryFactory dependent class for determining
    type of registry to create
    """

    in_memory: str = InMemoryTaskRegistry.__name__


_REGISTRY_CLASSES: dict[str, type[BaseTaskRegistry]] = {
    RegistryType.in_memory: InMemoryTaskRegistry,
}


class RegistryFactory:
    """
    Factory class for instantiating registry classes
    """

    @staticmethod
    def create_registry(registry_type: str) -> BaseTaskRegistry:
        """
        Creates registries

        parameters:
            registry_type (str): type of registry to create

        Returns:
            BaseTaskRegistry : created registry object
        """
        try:
            return _REGISTRY_CLASSES[registry_type]()
        except KeyError:
            raise ValueError(f"Unknown registry type: {registry_type}") from None
