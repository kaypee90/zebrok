import os
import socket
from .logging import create_logger

logger = create_logger(__name__)


def get_worker_port_and_host():
    """
    Retrieves port number and the host worker will
    be listening from configuration
    """
    port = None
    host = None

    try:
        from django.conf import settings

        if not port:
            port = settings.WORKER_PORT

        if not host:
            host = settings.WORKER_HOST
    except Exception:
        logger.warning("Attempt to load from django settings failed!")

    if not port:
        port = os.environ.get("WORKER_PORT")

    if not host:
        host = os.environ.get("WORKER_HOST")

    # Load default values
    if not port:
        from .config import WORKER_PORT

        port = WORKER_PORT

    if not host:
        from .config import WORKER_HOST

        host = WORKER_HOST

    return int(port), host
