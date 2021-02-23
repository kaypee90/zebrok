import os
from .logging import create_logger
from .config import WORKER_PORT, WORKER_HOST

logger = create_logger(__name__)


def get_worker_port_and_host():
    """
    Retrieves port number and the host worker will
    be listening from configuration
    """
    port = os.environ.get("WORKER_PORT", WORKER_PORT)
    host = os.environ.get("WORKER_HOST", WORKER_HOST)

    return int(port), host
