import inspect

class TaskRegistry(dict):
    
    def register(self, task):
        task = inspect.isclass(task) and task() or task
        self[task.get_task_object().__name__] = task

    def unregister(self, name):
        self.pop(getattr(name, 'name', name))
