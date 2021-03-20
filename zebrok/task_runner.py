from .exceptions import ZebrokNotImplementedError


class BaseTaskRunner(object):
    """
    All task runners implementation must inherit from this base class
    """

    def execute(self, task_name, **kwargs):
        raise ZebrokNotImplementedError


class DefaultTaskRunner(BaseTaskRunner):
    """
    Specialiazed task runner implementation
    for finding task in registry or through auto discovery feature
    and then executes it
    """

    def __init__(self, task_registry, auto_discover=False):
        self.auto_discover = auto_discover
        self.registry = task_registry

    def execute(self, task_name, **kwargs):
        """
        Executes provided task name with provided keyword
        arguments
        """
        return self._find_and_execute_task(task_name, **kwargs)

    def _find_and_execute_task(self, task_name, **kwargs):
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

