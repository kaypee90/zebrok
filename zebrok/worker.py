from .connection import SocketConnection
from .registry import InMemoryTaskRegistry
from .logging import create_logger
from .discovery import get_discovered_task_by_name

logger = create_logger(__name__)


class TaskRunner(object):

    def __init__(self, task_registry, auto_discover=False):
        self.auto_discover = auto_discover
        self.task_registry = task_registry

    def find_and_execute_task(self, task_name, **kwargs):
        '''
        Finds and execute tasks
        '''
        func = self.task_registry.get(task_name)
        if func:
            func(**kwargs)

        if not func and self.auto_discover:
            func = get_discovered_task_by_name(task_name)
            func(**kwargs)

        if not func:
            logger.error("Task not found!")


class Worker(object):

    def __init__(self, auto_discover=False, task_runner=None, task_registry=None):
        self.auto_discover = auto_discover
        self.sock, self.context = SocketConnection.initialize(bind_to_socket=False)
        self.tasks = task_registry if task_registry else InMemoryTaskRegistry()
        self.runner = task_runner if task_runner else TaskRunner(self.tasks, auto_discover)

    def register_task(self, task):
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
                self.runner.find_and_execute_task(task_name, **kwargs)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """
        Closes socket connection
        """
        self.sock.close()
        self.context.term()

