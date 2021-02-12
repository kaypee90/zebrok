from .connection import SocketConnection


class TaskPublisher(object):
    '''
    Publishes received tasks to worker
    '''
    
    @staticmethod
    def publish_task(task, *args, **kwargs):
        with SocketConnection(bind=True) as sock:
            payload = {"task": task.__name__, "kwargs": kwargs}
            sock.send_json(payload)
        return True


class Task(object):
    """
    Extends methods to be used with task queue
    """
    publisher = TaskPublisher

    def __init__(self, arg):
        self._arg = arg

    def __call__(self, *args, **kwargs):
        return self._arg(**kwargs)

    def get_task_object(self):
        return self._arg

    def run(self, *args, **kwargs):
        return self.publisher.publish_task(self._arg, *args, **kwargs)
