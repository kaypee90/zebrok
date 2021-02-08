from .connection import SocketConnection
from .registry import TaskRegistry
from .logging import create_logger
from .discovery import get_discovered_task_by_name

logger = create_logger(__name__)


class Worker(object):
    tasks = TaskRegistry()

    def __init__(self, auto_discover=False):
        self.sock, self.context = SocketConnection().connect_to_socket()
        self.auto_discover = auto_discover

    def _execute_task(self, task_name, **kwargs):
        '''
        Finds and execute tasks
        '''
        func = self.tasks.get(task_name)
        if func:
            func(**kwargs)

        if not func and self.auto_discover:
            func = get_discovered_task_by_name(task_name)
            func(**kwargs)

        if not func:
            logger.error("Task not found!")

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
                kwargs = message.pop("kwargs")
                logger.info(f"received task: {task_name}")
                self._execute_task(task_name, **kwargs)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """
        Closes socket connection
        """
        self.sock.close()
        self.context.term()
