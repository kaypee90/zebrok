from .connection import SocketType, ConnectionType, ConnectionFactory
from .utils import get_worker_port_and_host


class TaskPublisher(object):
    """
    Handles pushing of tasks to task queue
    """

    def __init__(self):
        port, host = get_worker_port_and_host()
        settings = (
            SocketType.ZmqPush,
            host,
            port,
        )
        self.connection = ConnectionFactory.create_connection(
            ConnectionType.zmq_connect, *settings
        )
        self.socket = self.connection.socket

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.connection.close()

    def publish_task(self, task, *args, **kwargs):
        payload = {"task": task.__name__, "kwargs": kwargs}
        self.socket.send_json(payload)
        return True


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
        with TaskPublisher() as publisher:
            return publisher.publish_task(self._arg, *args, **kwargs)
