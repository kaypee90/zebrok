import json
import signal
import threading
from collections.abc import Callable
from typing import Any

import zmq

from .config import WORKER_POLL_INTERVAL_MS
from .connection import (
    BaseSocketConnection,
    ConnectionFactory,
    ConnectionType,
    SocketType,
)
from .discovery import discover_tasks
from .logging import create_logger
from .registry import BaseTaskRegistry, RegistryFactory, RegistryType
from .task_runner import BaseTaskRunner, DefaultTaskRunner
from .utils import get_worker_port_and_host

logger = create_logger(__name__)


class TaskQueueWorker:
    """
    Listens and receives tasks and uses a task runner to execute them
    """

    def __init__(
        self,
        connection: BaseSocketConnection,
        runner: BaseTaskRunner,
        poll_interval_ms: int = WORKER_POLL_INTERVAL_MS,
    ) -> None:
        self.slaves: list[Any] = []
        self.connection = connection
        self.socket = self.connection.socket
        self.runner = runner
        self.current_slave = 0
        self.poll_interval_ms = poll_interval_ms
        self._slave_poller = zmq.Poller()
        self._stop_event = threading.Event()
        # Guards _running/_closed so the sockets are closed exactly once, by
        # the loop's own thread when it is running.
        self._state_lock = threading.RLock()  # re-entrant: signal handlers call stop()
        self._running = False
        self._closed = False

    def start(self) -> None:
        """
        Listens for new tasks until stop() is called.
        Tasks are executed immediately if there are no slave workers available
        else they are pushed to a slave worker using round robin scheduling.

        The loop wakes up every poll_interval_ms to check for a stop request,
        and this worker's sockets are closed in this thread when it exits
        (zmq sockets must not be shared between threads).
        """
        with self._state_lock:
            if self._closed or self._stop_event.is_set():
                return
            self._running = True
        logger.info(f"starting worker on: {self.connection.socket_address}")
        try:
            while not self._stop_event.is_set():
                if self.socket.poll(self.poll_interval_ms):
                    self.handle_message(self.socket.recv())
        finally:
            with self._state_lock:
                self._running = False
                self._close_sockets()

    def handle_message(self, data: bytes) -> None:
        """
        Forwards a raw message to a slave, or decodes and executes it.
        Never raises (except KeyboardInterrupt): a bad message or a failing
        task, even one calling sys.exit(), must not stop the worker.
        """
        try:
            if self.number_of_slaves > 0:
                self._forward_to_slave(data)
                return
            task_name, args, kwargs = self._decode(data)
            logger.info(f"received task: {task_name}")
            self.runner.execute(task_name, *args, **kwargs)
        except (Exception, SystemExit):
            logger.exception("failed to process message")

    def _forward_to_slave(self, data: bytes) -> None:
        """
        Hands a message to the next slave that can take it, without ever
        blocking indefinitely: if every slave is busy (queue full) the master
        waits for one to free up, but gives up once stop() is requested.
        """
        while not self._stop_event.is_set():
            for _ in range(self.number_of_slaves):
                try:
                    self.get_available_slave().send(data, zmq.NOBLOCK)
                    logger.debug("sent task to slave worker")
                    return
                except zmq.Again:
                    continue
            self._slave_poller.poll(self.poll_interval_ms)
        logger.warning("worker stopping, dropped a task no slave could accept")

    @staticmethod
    def _decode(data: bytes) -> tuple[str, list, dict]:
        message = json.loads(data)
        if not isinstance(message, dict) or not isinstance(message.get("task"), str):
            raise TypeError(f"malformed task message: {message!r}")
        args = message.get("args") or []
        kwargs = message.get("kwargs") or {}
        if not isinstance(args, list) or not isinstance(kwargs, dict):
            raise TypeError(f"malformed task arguments: {message!r}")
        return message["task"], args, kwargs

    @property
    def number_of_slaves(self) -> int:
        """
        Number of slave workers initialized
        """
        return len(self.slaves)

    def get_available_slave(self) -> Any:
        """
        Uses round robin to cycle through and return available slave worker
        """
        slave_push_socket = self.slaves[self.current_slave]
        self.current_slave = (self.current_slave + 1) % self.number_of_slaves
        return slave_push_socket

    def stop(self) -> None:
        """
        Asks the worker loop to exit. Safe to call from any thread, any number
        of times; the loop notices within poll_interval_ms. If the worker is
        not running its sockets are closed immediately.
        """
        self._stop_event.set()
        with self._state_lock:
            if not self._running:
                self._close_sockets()

    def _close_sockets(self) -> None:
        """
        Must be called with _state_lock held
        """
        if self._closed:
            return
        self._closed = True
        for slave_socket in self.slaves:
            slave_socket.close(linger=0)
        self.connection.close(linger=0)

    def add_slave(self, worker: Any) -> None:
        """
        Adds a slave worker to a master worker
        """
        self.slaves.append(worker)
        self._slave_poller.register(worker, zmq.POLLOUT)


class WorkerInitializer:
    """
    Initializes workers and all its dependencies
    """

    def __init__(
        self,
        number_of_slaves: int = 0,
        auto_discover: bool = False,
        task_registry: BaseTaskRegistry | None = None,
        max_retries: int = 0,
        retry_delay: float = 0.0,
    ) -> None:
        """
        parameters:
            number_of_slaves (int): worker threads the master hands tasks to.
                With 0 the master runs tasks itself
            auto_discover (bool): look tasks up in the tasks module
            task_registry: registry to use (default: in-memory)
            max_retries (int): extra attempts for a task that raises
            retry_delay (float): seconds to wait between attempts
        """
        if not isinstance(number_of_slaves, int) or number_of_slaves < 0:
            raise ValueError("number_of_slaves must be a non-negative integer")
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        if retry_delay < 0:
            raise ValueError("retry_delay must be zero or positive")
        self.tasks = self._initialize_registry(task_registry)
        self._runner: BaseTaskRunner | None = None
        self.number_of_slaves = number_of_slaves
        self.auto_discover = auto_discover
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # _lock guards the lifecycle state below. A stop() swaps the state
        # out under the lock, so exactly one caller tears down.
        self._lock = threading.Lock()
        self._context: zmq.Context | None = None
        self._master: TaskQueueWorker | None = None
        self._workers: list[TaskQueueWorker] = []
        self._threads: list[threading.Thread] = []
        self._master_thread: threading.Thread | None = None
        # Thread running a blocking start(); only it tears down in that mode.
        self._blocking_thread: threading.Thread | None = None
        self._stopping = False

    def register_task(self, task: Any) -> None:
        """
        Registers tasks to in-memory task registry
        """
        self.tasks.register(task)

    def _initialize_registry(
        self,
        task_registry: BaseTaskRegistry | None,
    ) -> BaseTaskRegistry:
        """
        Get registry instance to be used by the task runner
        """
        if task_registry is not None:
            return task_registry
        return RegistryFactory.create_registry(RegistryType.in_memory)

    @property
    def runner(self) -> BaseTaskRunner:
        """
        Task Runner used for executing received tasks. The default runner is
        created once and then reused.
        """
        if self._runner is None:
            self._runner = DefaultTaskRunner(
                self.tasks,
                self.auto_discover,
                self.max_retries,
                self.retry_delay,
            )
        return self._runner

    @runner.setter
    def runner(self, custom_runner: BaseTaskRunner | None) -> None:
        """
        Sets a custom task runner to be used by workers
        """
        if custom_runner is not None and not isinstance(custom_runner, BaseTaskRunner):
            raise TypeError(
                f"{type(custom_runner)} must inherit from {BaseTaskRunner}",
            )
        self._runner = custom_runner

    @property
    def is_running(self) -> bool:
        return self._master is not None

    def _initialize_workers(self) -> None:
        """
        Creates the master worker (bound to WORKER_HOST:WORKER_PORT) and its
        slave workers. Slaves are linked to the master over in-process
        (inproc) sockets, so they need no extra TCP ports.
        """
        port, host = get_worker_port_and_host()
        context = zmq.Context()
        connections: list[BaseSocketConnection] = []
        workers: list[TaskQueueWorker] = []
        try:
            master_connection = self._create_socket_connection(
                ConnectionType.zmq_bind,
                SocketType.ZmqPull,
                host,
                port,
                context,
            )
            connections.append(master_connection)
            master = self._create_task_queue_worker(master_connection)

            for i in range(self.number_of_slaves):
                address = f"inproc://zebrok-{id(self)}-slave-{i}"
                push_connection = self._create_socket_connection(
                    ConnectionType.zmq_bind,
                    SocketType.ZmqPush,
                    host,
                    port,
                    context,
                    address=address,
                )
                connections.append(push_connection)
                master.add_slave(push_connection.socket)

                pull_connection = self._create_socket_connection(
                    ConnectionType.zmq_connect,
                    SocketType.ZmqPull,
                    host,
                    port,
                    context,
                    address=address,
                )
                connections.append(pull_connection)
                workers.append(self._create_task_queue_worker(pull_connection))
        except BaseException:
            for connection in connections:
                connection.close(linger=0)
            context.term()
            raise

        self._context = context
        self._master = master
        self._workers = workers

    def _create_socket_connection(
        self,
        connection_type: str,
        *settings: Any,
        **kwargs: Any,
    ) -> BaseSocketConnection:
        """
        Creates socket connections using the Connection Factory
        """
        return ConnectionFactory.create_connection(connection_type, *settings, **kwargs)

    def _create_task_queue_worker(
        self,
        connection: BaseSocketConnection,
    ) -> TaskQueueWorker:
        """
        Creates a new task queue
        """
        return TaskQueueWorker(connection, self.runner)

    def _start_thread(self, worker: TaskQueueWorker, name: str) -> threading.Thread:
        def run() -> None:
            try:
                worker.start()
            except BaseException:
                logger.exception(f"{name} crashed")

        thread = threading.Thread(target=run, name=name, daemon=True)
        thread.start()
        self._threads.append(thread)
        return thread

    def start(self, block: bool = True) -> None:
        """
        Scan for tasks if auto discover is set to True and
        start workers to be receiving incoming messages.

        parameters:
            block (bool): when True (default) run until Ctrl+C / SIGTERM or
                until stop() is called from another thread, then shut down
                cleanly and return. When False, run in background threads
                and return immediately; call stop() to shut down.
        """
        with self._lock:
            if self._master is not None or self._stopping:
                raise RuntimeError("Worker is already running")
            if self.auto_discover:
                discover_tasks()
            self._initialize_workers()
            assert self._master is not None
            master = self._master

            for i, worker in enumerate(self._workers):
                self._start_thread(worker, f"zebrok-slave-{i}")

            if not block:
                self._master_thread = self._start_thread(master, "zebrok-master")
                return
            self._blocking_thread = threading.current_thread()

        restore_signals = self._install_signal_handlers(master)
        try:
            master.start()
        except KeyboardInterrupt:
            logger.info("interrupted, shutting down workers")
        finally:
            restore_signals()
            with self._lock:
                self._blocking_thread = None
            self.stop()

    def _install_signal_handlers(self, master: TaskQueueWorker) -> Callable[[], None]:
        """
        Makes SIGTERM (sent by docker/k8s) and the first Ctrl+C stop the
        worker gracefully: running tasks finish, then start() returns.
        A second Ctrl+C interrupts immediately. Only possible from the main
        thread; returns a function that restores the previous handlers.
        """
        if threading.current_thread() is not threading.main_thread():
            return lambda: None

        def on_signal(signum: int, frame: Any) -> None:
            logger.info(
                f"received {signal.Signals(signum).name}, finishing running "
                "tasks (press Ctrl+C again to force)",
            )
            signal.signal(signal.SIGINT, signal.default_int_handler)
            master.stop()

        previous = {
            sig: signal.signal(sig, on_signal)
            for sig in (signal.SIGINT, signal.SIGTERM)
        }

        def restore() -> None:
            for sig, handler in previous.items():
                signal.signal(sig, handler)

        return restore

    def stop(self, timeout: float | None = None) -> None:
        """
        Stops the master and all slave workers. Tasks that are already
        executing are allowed to finish; tasks still queued are dropped.
        Safe to call from any thread and more than once.

        While a blocking start() is running, calling stop() from another
        thread only signals it; the thread running start() then shuts
        everything down and start() returns.

        parameters:
            timeout (float): seconds to wait for each worker thread
        """
        with self._lock:
            master = self._master
            if master is None:
                return
            blocking = self._blocking_thread
            if blocking is not None and blocking is not threading.current_thread():
                master.stop()
                return
            # Take ownership of the teardown; concurrent callers return above.
            workers, threads = self._workers, self._threads
            master_thread, context = self._master_thread, self._context
            self._master = None
            self._workers, self._threads = [], []
            self._master_thread = self._context = None
            self._stopping = True

        try:
            current = threading.current_thread()
            # Stop the master first so it never forwards to a stopped slave.
            master.stop()
            if master_thread is not None and master_thread is not current:
                master_thread.join(timeout)
            for worker in workers:
                worker.stop()
            for thread in threads:
                if thread is not current and thread is not master_thread:
                    thread.join(timeout)

            alive = [t.name for t in threads if t.is_alive() and t is not current]
            if current in threads:
                # stop() called from inside a task: that thread's sockets are
                # closed when it returns to its loop, so term() would block.
                alive.append(current.name)
            if context is not None:
                if alive:
                    logger.warning(f"workers still busy, not waiting for: {alive}")
                    # term() blocks until they close their sockets, so let a
                    # helper thread finish the cleanup once they do.
                    threading.Thread(
                        target=context.term,
                        name="zebrok-context-term",
                        daemon=True,
                    ).start()
                else:
                    context.term()
        finally:
            with self._lock:
                self._stopping = False
