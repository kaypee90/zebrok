import concurrent.futures
from .task_runner import DefaultTaskRunner, BaseTaskRunner
from .connection import SocketType, ConnectionType, ConnectionFactory
from .registry import RegistryType, RegistryFactory
from .logging import create_logger
from .discovery import discover_tasks
from .utils import get_worker_port_and_host


logger = create_logger(__name__)


class TaskQueueWorker(object):
    """
    Listens and receives tasks and uses a task runner to execute them
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
                    slave_push_socket = self.get_available_slave()
                    slave_push_socket.send_json(message)
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

    def get_available_slave(self):
        """
        Uses round robin to cycle through and return available slave worker
        """
        slave_push_socket = self.slaves[self.current_slave]
        self.current_slave += 1
        if self.current_slave == self.number_of_slaves:
            self.current_slave = 0
        return slave_push_socket

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
        """
        Sets a custom task runner to be used by workers
        """
        if custom_runner:
            assert issubclass(
                type(custom_runner), BaseTaskRunner
            ), "{} must inherit from {}".format(
                type(custom_runner), str(BaseTaskRunner)
            )
        self._runner = custom_runner

    def _initialize_workers(self):
        """
        Initializes master and slave workers
        """
        port, host = get_worker_port_and_host()
        max_workers = self.number_of_slaves + 1
        master_settings = (
            SocketType.ZmqPull,
            host,
            port,
        )
        master_socket, master_worker = self._create_master_worker(*master_settings)
        self._initialize_slave_workers(
            max_workers, host, port, master_socket, master_worker
        )

    def _create_master_worker(self, *settings):
        """
        Creates the main worker
        """
        socket = self._create_socket_connection(ConnectionType.zmq_bind, *settings)
        worker = self._create_task_queue_worker(socket)
        return socket, worker

    def _initialize_slave_workers(
        self, max_workers, host, port, master_socket, master_worker
    ):
        """
        Creates worker threads as slaves to be associated with the main worker
        """
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
        """
        Creates push connection type for sending tasks to slaves
        """
        return self._create_socket_connection(ConnectionType.zmq_bind, *settings)

    def _create_slave_worker(self, *settings):
        """
        Creates a slave task queue worker associated with the master
        """
        pull_connection = self._create_socket_connection(
            ConnectionType.zmq_connect, *settings
        )
        return self._create_task_queue_worker(pull_connection)

    def _create_socket_connection(self, connection_type, *settings):
        """
        Creates socket connections using the Connection Factory
        """
        return ConnectionFactory.create_connection(connection_type, *settings)

    def _create_task_queue_worker(self, connection):
        """
        Creates a new task queue
        """
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
