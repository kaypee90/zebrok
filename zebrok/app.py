from .connection import SocketConnection


class Task(object):
    """
    Extends methods to be used with task queue
    """

    def __init__(self, arg):
        self._arg = arg

    def __call__(self, *args, **kwargs):
        return self._arg(**kwargs)

    def get_task_object(self):
        return self._arg

    def run(self, *args, **kwargs):
        payload = {"task": self._arg.__name__, "kwargs": kwargs}
        return self._publish_task(payload)

    @classmethod
    def _publish_task(cls, task_payload):
        sock, context = SocketConnection.bind_to_socket()
        sock.send_json(task_payload)
        sock.close()
        context.term()
        return True
