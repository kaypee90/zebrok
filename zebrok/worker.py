import concurrent.futures
from .connection import SocketType, ConnectionType, ConnectionFactory
from .registry import RegistryType, RegistryFactory
from .logging import create_logger
from .discovery import get_discovered_task_by_name, discover_tasks
from .utils import get_worker_port_and_host
from .exceptions import ZebrokNotImplementedError

logger = create_logger(__name__)


class BaseTaskRunner(object):
    """
    All task runners implementation must inherit from this base class
    """

    def execute(self, task_name, **kwargs):
        raise ZebrokNotImplementedError


class DefaultTaskRunner(BaseTaskRunner):
    """
    Specialiazed task runner implementation
    for finding task in registry or through auto discovery feature
    and then executes it
    """

    def __init__(self, task_registry, auto_discover=False):
        self.auto_discover = auto_discover
        self.registry = task_registry

    def execute(self, task_name, **kwargs):
        """
        Executes provided task name with provided keyword
        arguments
        """
        return self._find_and_execute_task(task_name, **kwargs)

    def _find_and_execute_task(self, task_name, **kwargs):
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
    """
    Listens and receives tasks and uses a runner to execute it
    """

    def __init__(self, connection, runner):
        self.slaves = []
        self.connection = connection
        self.socket = self.connection.socket
        self.runner = runner
        self.current_slave = 0

    def start(self):
        """
        Establishes a socket connection which listens for new tasks.
        Tasks are executed immediately if there are no slave workers available else
        they are pushed to a slave worker using round robin scheduling.
        """
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
                    self.runner.execute(task_name, **kwargs)
        except KeyboardInterrupt:
            self.stop()

    @property
    def number_of_slaves(self):
        """
        Number of slave workers initialized
        """
        return len(self.slaves)

    def increment_current_slave(self):
        """
        Increase count of initialized slaves
        """
        self.current_slave += 1
        if self.current_slave == self.number_of_slaves:
            self.current_slave = 0

    def stop(self):
        """
        Close socket connection
        """
        self.current_slave = 0
        self.connection.close()

    def add_slave(self, worker):
        """
        Add a slave worker to a master worker
        """
        self.slaves.append(worker)


class WorkerInitializer(object):
    """
    Initializes workers and all its dependencies
    """

    def __init__(self, number_of_slaves=0, auto_discover=False, task_registry=None):
        self.tasks = self._initialize_registry(task_registry)
        self._runner = None
        self.number_of_slaves = number_of_slaves
        self.auto_discover = auto_discover

    def register_task(self, task):
        """
        Registers tasks to in-memory task registry
        """
        self.tasks.register(task)

    def _initialize_registry(self, task_registry):
        """
        Get registry instance to be used by the task runner
        """
        return task_registry or RegistryFactory.create_registry(RegistryType.in_memory)

    @property
    def runner(self):
        """
        Get instance of Task Runner to be used for executing received tasks
        """
        return self._runner or DefaultTaskRunner(self.tasks, self.auto_discover)

    @runner.setter
    def runner(self, custom_runner):
        if custom_runner:
            assert issubclass(
                type(custom_runner), BaseTaskRunner
            ), "{} must inherit from {}".format(
                type(custom_runner), str(BaseTaskRunner)
            )
        self._runner = custom_runner

    def _initialize_workers(self):
        port, host = get_worker_port_and_host()
        max_workers = self.number_of_slaves + 1
        master_settings = (
            SocketType.ZmqPull,
            host,
            port,
        )
        master_socket, master_worker = self._create_master_worker(*master_settings)
        self._initialize_slave_workers(max_workers, host, port, master_socket, master_worker)

    def _create_master_worker(self, *settings):
        socket = self._create_socket_connection(
            ConnectionType.zmq_bind, *settings
        )
        worker = self._create_task_queue_worker(socket)
        return socket, worker

    def _initialize_slave_workers(self, max_workers, host, port, master_socket, master_worker):
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
        return self._create_socket_connection(ConnectionType.zmq_bind, *settings)

    def _create_slave_worker(self, *settings):
        pull_connection = self._create_socket_connection(
            ConnectionType.zmq_connect, *settings
        )
        return self._create_task_queue_worker(pull_connection)

    def _create_socket_connection(self, connection_type, *settings):
        return ConnectionFactory.create_connection(connection_type, *settings)

    def _create_task_queue_worker(self, connection):
        return TaskQueueWorker(connection, self.runner)

    def start(self):
        """
        Scan for tasks if auto discover is set to True and  
        start workers to be receiving incoming
        messages
        """
        if self.auto_discover:
            discover_tasks()
        self._initialize_workers()
