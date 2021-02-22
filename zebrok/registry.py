import inspect
from abc import ABC, abstractmethod


class BaseTaskRegistry(ABC):
    """
    Concrete task registry types must
    inherit this abstract class
    """

    @abstractmethod
    def register(self, task):
        raise NotImplementedError

    @abstractmethod
    def unregister(self, name):
        raise NotImplementedError


class InMemoryTaskRegistry(BaseTaskRegistry, dict):
    """
    In-memory implementation of Task registry
    """

    def register(self, task):
        """
        Adds a task to in-memory registry
        """
        task = inspect.isclass(task) and task() or task
        self[task.get_task_object().__name__] = task

    def unregister(self, name):
        """
        Removes a task to in-memory registry
        """
        self.pop(getattr(name, "name", name))


class RegistryType:
    """
    RegistryFactory dependent class for determining
    type of registry to create
    """

    in_memory = InMemoryTaskRegistry.__name__


class RegistryFactory:
    """
    Factory class for instantiating registry classes
    """

    @staticmethod
    def create_registry(registry_type):
        registry = globals()[registry_type]()
        assert issubclass(
            type(registry), BaseTaskRegistry
        ), "{} must inherit from {}".format(type(registry), str(BaseTaskRegistry))
        return registry
