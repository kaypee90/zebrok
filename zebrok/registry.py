import inspect
from abc import ABC, abstractmethod
from .exceptions import ZebrokNotImplementedError


class BaseTaskRegistry(ABC):
    """
    Concrete task registry types must
    inherit this abstract class
    """

    @abstractmethod
    def register(self, task):
        """
        Add a new task to the registry

        parameters:
            task (object): the function to be added to the registry
        """
        raise ZebrokNotImplementedError

    @abstractmethod
    def unregister(self, name):
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
        """
        Creates registries

        parameters:
            registry_type (str): type of registry to create

        Returns:
            BaseTaskRegistry : created registry
        """
        registry = globals()[registry_type]()
        assert issubclass(
            type(registry), BaseTaskRegistry
        ), "{} must inherit from {}".format(type(registry), str(BaseTaskRegistry))
        return registry
