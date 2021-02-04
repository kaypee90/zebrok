from .connection import SocketConnection
from .utils import unpickle_task
from .registry import TaskRegistry


class Worker(object):
    tasks = TaskRegistry()

    def __init__(self):
        self.sock = SocketConnection().connect_to_socket()

    def register(self, task):
        """
        Registers tasks to in-memory task registry
        """
        self.tasks.register(task)

    def start(self):
        """
        Starts worker to be receiving incoming
        messages
        """
        try:
            while True:
                message = self.sock.recv()
                payload = unpickle_task(message)
                func = self.tasks.get(payload["task"])
                kwargs = payload["kwargs"]
                func(**kwargs)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """
        Closes socket connection
        """
        self.sock.close()
