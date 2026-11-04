import os

from .config import PUBLISH_TIMEOUT_MS, TASKS_MODULE, WORKER_HOST, WORKER_PORT


def get_worker_port_and_host() -> tuple[int, str]:
    """
    Retrieves port number and the host worker
    will be listening from configuration
    """
    port = os.environ.get("WORKER_PORT", WORKER_PORT)
    host = os.environ.get("WORKER_HOST", WORKER_HOST)

    return int(port), host


def get_publish_timeout_ms() -> int:
    """
    Retrieves how long publishers wait for a worker before giving up
    """
    timeout = int(os.environ.get("ZEBROK_PUBLISH_TIMEOUT_MS", PUBLISH_TIMEOUT_MS))
    return validate_timeout_ms(timeout, "ZEBROK_PUBLISH_TIMEOUT_MS")


def validate_timeout_ms(timeout_ms: int, name: str = "timeout_ms") -> int:
    """
    Publish timeouts must be positive: 0 would fail before a connection is
    established, and negative values mean "wait forever" in zmq.
    """
    if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int):
        raise TypeError(f"{name} must be an integer number of milliseconds")
    if timeout_ms <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return timeout_ms


def get_tasks_module_name() -> str:
    """
    Retrieves the name of the module scanned by auto discovery
    """
    return os.environ.get("ZEBROK_TASKS_MODULE", TASKS_MODULE)
