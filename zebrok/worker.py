from .connection import SocketConnection
from .registry import TaskRegistry
from .logger import setup_logging

logger = setup_logging(__name__)


class Worker(object):
    tasks = TaskRegistry()

    def __init__(self, auto_discover=False):
        self.sock, self.context = SocketConnection().connect_to_socket()
        self.auto_discover = auto_discover

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
                message = self.sock.recv_json()
                task_name = message.pop("task")
                logger.info(f"received task: {task_name}")
                func = self.tasks.get(task_name)
                kwargs = message.pop("kwargs")
                func(**kwargs)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """
        Closes socket connection
        """
        self.sock.close()
        self.context.term()
