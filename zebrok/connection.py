import enum
import socket
from typing import Any

import zmq

from .exceptions import ZebrokNotImplementedError


class SocketType(enum.Enum):
    """
    Type of socket connection to be established
    """

    ZmqPull = zmq.PULL
    ZmqPush = zmq.PUSH


def convert_hostname_to_ip(hostname: str) -> str:
    """
    Converts host name to an ip address

    Parameters:
        hostname (str): name of host

    Returns:
        str : converted ip address for host
    """
    return hostname if hostname == "*" else socket.gethostbyname(hostname)


class BaseSocketConnection:
    """
    All connection implementation must inherit from this base class

    socket_type = type of connection created by factory
    host = name of the host on which connection is being created
    port = socket connection port
    socket_address = address for establishing the connection
    context = current connection context
    socket = created socket connection
    owns_context = True when the context was created by this connection and
                   must therefore be terminated when the connection closes
    """

    def __init__(
        self,
        socket_type: SocketType,
        host: str,
        port: int | str,
        context: zmq.Context | None = None,
        address: str | None = None,
        socket_options: dict[int, Any] | None = None,
    ) -> None:
        """
        parameters:
            socket_type (SocketType): type of socket to initialize
            host (str): The host ip to use
            port (int): Port number to connect or listen on
            context (object): Zmq context to create the socket in. A new one
                is created (and owned by this connection) when omitted
            address (str): Full zmq address (e.g. "inproc://name"). When
                given, host and port are not used to build the address
            socket_options (dict): zmq socket options applied before the
                socket binds/connects (some, like IMMEDIATE, only take
                effect if set first)
        """
        self.socket_type = socket_type.value
        self.port = int(port)
        if address:
            self.host = host
            self.socket_address = address
        else:
            self.host = convert_hostname_to_ip(host)
            self.socket_address = self.get_socket_address()
        self.owns_context = context is None
        self.context = zmq.Context() if context is None else context
        self.socket: Any = None
        if type(self)._open is BaseSocketConnection._open:
            # Subclass written against the old API: it creates and
            # binds/connects the socket itself after calling super().__init__.
            return
        self.socket = self.context.socket(self.socket_type)
        try:
            for option, value in (socket_options or {}).items():
                self.socket.setsockopt(option, value)
            self._open()
        except Exception:
            self.close(linger=0)
            raise

    def _open(self) -> None:
        """
        Binds or connects the underlying socket
        """
        raise ZebrokNotImplementedError

    def close(self, linger: int | None = None) -> None:
        """
        Closes the underlying socket, and terminates the context if this
        connection created it.

        parameters:
            linger (int): milliseconds to wait for unsent messages to be
                delivered before discarding them (None = zmq default)
        """
        if self.socket is not None and not self.socket.closed:
            self.socket.close(linger=linger)
        if self.owns_context and not self.context.closed:
            self.context.term()

    def get_socket_address(self) -> str:
        """
        Constructs tcp adddress to be connected to
        Returns:
            (str): constructed socket address using host and port
        """
        return f"tcp://{self.host}:{self.port}"


class ZmqBindConnection(BaseSocketConnection):
    """
    Specialized 0mq socket binding implementation
    """

    def _open(self) -> None:
        self.socket.bind(self.socket_address)


class ZmqConnectTypeConnection(BaseSocketConnection):
    """
    Specialized 0mq socket connection implementation
    """

    def _open(self) -> None:
        self.socket.connect(self.socket_address)


class ConnectionType:
    """
    ConnectionFactory dependent class for determining
    which connection type to create
    """

    zmq_bind = ZmqBindConnection.__name__
    zmq_connect = ZmqConnectTypeConnection.__name__


_CONNECTION_CLASSES: dict[str, type[BaseSocketConnection]] = {
    ConnectionType.zmq_bind: ZmqBindConnection,
    ConnectionType.zmq_connect: ZmqConnectTypeConnection,
}


class ConnectionFactory:
    """
    Factory class fo instantiating socket connections
    """

    @staticmethod
    def create_connection(
        connection_type: str,
        *args: Any,
        **kwargs: Any,
    ) -> BaseSocketConnection:
        """
        Creates sockect connections

        parameters:
            connection_type (str): Type of connection to create

        Returns:
            BaseSocketConnection : created socket connection
        """
        try:
            connection_class = _CONNECTION_CLASSES[connection_type]
        except KeyError:
            raise ValueError(f"Unknown connection type: {connection_type}") from None
        return connection_class(*args, **kwargs)
