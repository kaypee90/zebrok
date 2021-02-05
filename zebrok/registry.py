import inspect


class TaskRegistry(dict):
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
