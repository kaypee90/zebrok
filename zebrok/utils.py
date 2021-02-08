import os
import socket
from .logger import setup_logging

logger = setup_logging(__name__)


def get_socket_address_from_conf():
    """
    Retrieves socket address configuration
    """
    port, host = get_publisher_port_and_host()
    host_ip = resolve_hostname(host)
    socket_address = f"tcp://{host_ip}:{str(port)}"

    logger.info(f"Connecting on {socket_address}")
    return socket_address


def resolve_hostname(host):
    return socket.gethostbyname(host)


def get_publisher_port_and_host():
    """
    Retrieves port number and the host publisher will
    be listening from configuration
    """
    port = None
    host = None

    try:
        from django.conf import settings

        if not port:
            port = settings.PUBLISHER_PORT

        if not host:
            host = settings.PUBLISHER_HOST
    except Exception:
        logger.warning("Attempt to load from django settings failed!")

    if not port:
        port = os.environ.get("PUBLISHER_PORT")

    if not host:
        host = os.environ.get("PUBLISHER_HOST")

    # Load default values
    if not port:
        from .config import PUBLISHER_PORT

        port = PUBLISHER_PORT

    if not host:
        from .config import PUBLISHER_HOST

        host = PUBLISHER_HOST

    return port, host
