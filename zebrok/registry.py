import inspect
from abc import ABC, abstractmethod


class BaseTaskRegistry(ABC):
    '''
    Concrete task registry types must
    inherit this absract class
    '''
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
        '''
        Adds a task to in-memory registry
        '''
        task = inspect.isclass(task) and task() or task
        self[task.get_task_object().__name__] = task

    def unregister(self, name):
        '''
        Removes a task to in-memory registry
        '''
        self.pop(getattr(name, "name", name))
