import os
from typing import Tuple

from .config import WORKER_HOST
from .config import WORKER_PORT
from .logging import create_logger

logger = create_logger(__name__)


def get_worker_port_and_host() -> Tuple[int, str]:
    """
    Retrieves port number and the host worker
    will be listening from configuration
    """
    port = os.environ.get("WORKER_PORT", WORKER_PORT)
    host = os.environ.get("WORKER_HOST", WORKER_HOST)

    return int(port), host
