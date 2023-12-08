from .connection import ConnectionFactory
from .connection import ConnectionType
from .connection import SocketType
from .utils import get_worker_port_and_host
from typing import Callable, Dict, Tuple, Any


class TaskPublisher:
    """
    Handles pushing of tasks to task queue
    """

    def __init__(self) -> None:
        port, host = get_worker_port_and_host()
        settings = (
            SocketType.ZmqPush,
            host,
            port,
        )
        self.connection = ConnectionFactory.create_connection(
            ConnectionType.zmq_connect,
            *settings,
        )
        self.socket = self.connection.socket

    def __enter__(self) -> "TaskPublisher":
        return self

    def __exit__(self, type: Any, value: Any, traceback: Any) -> None:
        self.connection.close()

    def publish_task(self, task: Callable[..., Any], *args: Tuple, **kwargs: Dict):
        payload = {"task": task.__name__, "kwargs": kwargs}
        self.socket.send_json(payload)
        return True


class Task:
    """
    Extends the methods to be used with task queue
    """

    def __init__(self, arg: Callable[..., Any]) -> None:
        self._arg = arg

    def __call__(self, *args: Tuple, **kwargs: Dict):
        return self._arg(**kwargs)

    def get_task_object(self) -> Callable[..., Any]:
        return self._arg

    def run(self, *args: Tuple, **kwargs: Dict) -> bool:
        with TaskPublisher() as publisher:
            return publisher.publish_task(self._arg, *args, **kwargs)
