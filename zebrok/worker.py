import concurrent.futures
from .connection import SocketType, ConnectionType, ConnectionFactory
from .registry import RegistryType, RegistryFactory
from .logging import create_logger
from .discovery import get_discovered_task_by_name
from .utils import get_worker_port_and_host

logger = create_logger(__name__)


class TaskRunner(object):
    def __init__(self, task_registry, auto_discover=False):
        self.auto_discover = auto_discover
        self.registry = task_registry

    def find_and_execute_task(self, task_name, **kwargs):
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


class TaskQueueWorker(object):
    def __init__(self, connection, runner):
        self.slaves = []
        self.connection = connection
        self.socket = self.connection.socket
        self.runner = runner
        self.current_slave = 0

    def start(self):
        logger.info(f"starting worker on: {self.connection.socket_address}")
        try:
            while True:
                message = self.socket.recv_json()
                if self.number_of_slaves > 0:
                    logger.info("sending task to slave worker")
                    push_socket = self.slaves[self.current_slave]
                    push_socket.send_json(message)
                    self.increment_current_slave()
                else:
                    task_name = message.pop("task")
                    kwargs = message.pop("kwargs")
                    logger.info(f"received task: {task_name}")
                    self.runner.find_and_execute_task(task_name, **kwargs)
        except KeyboardInterrupt:
            self.stop()

    @property
    def number_of_slaves(self):
        return len(self.slaves)

    def increment_current_slave(self):
        self.current_slave += 1
        if self.current_slave == self.number_of_slaves:
            self.current_slave = 0

    def stop(self):
        self.current_slave = 0
        self.connection.close()

    def add_slave(self, worker):
        self.slaves.append(worker)


class WorkerInitializer(object):
    def __init__(self, number_of_slaves=0, auto_discover=False, task_registry=None):
        self.tasks = task_registry or RegistryFactory.create_registry(
            RegistryType.in_memory
        )
        self.runner = TaskRunner(self.tasks, auto_discover)
        self.number_of_slaves = number_of_slaves

    def register_task(self, task):
        """
        Registers tasks to in-memory task registry
        """
        self.tasks.register(task)

    def _initialize_workers(self):
        port, host = get_worker_port_and_host()
        max_workers = self.number_of_slaves + 1
        master_settings = (
            SocketType.ZmqPull,
            host,
            port,
        )
        master_socket = ConnectionFactory.create_connection(
            ConnectionType.zmq_bind, *master_settings
        )
        master_worker = TaskQueueWorker(master_socket, self.runner)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(self.number_of_slaves):
                slave_port = port + i + 1

                push_slave_settings = (
                    SocketType.ZmqPush,
                    host,
                    slave_port,
                    master_socket.context,
                )
                push_connection = self._create_slave_push_connection(
                    *push_slave_settings
                )
                master_worker.add_slave(push_connection.socket)

                pull_slave_settings = (
                    SocketType.ZmqPull,
                    host,
                    slave_port,
                )
                slave_worker = self._create_slave_worker(*pull_slave_settings)
                executor.submit(slave_worker.start)

            executor.submit(master_worker.start)

    def _create_slave_push_connection(self, *settings):
        return ConnectionFactory.create_connection(ConnectionType.zmq_bind, *settings)

    def _create_slave_worker(self, *settings):
        pull_connection = ConnectionFactory.create_connection(
            ConnectionType.zmq_connect, *settings
        )
        return TaskQueueWorker(pull_connection, self.runner)

    def start(self):
        """
        Starts workers to be receiving incoming
        messages
        """
        self._initialize_workers()
