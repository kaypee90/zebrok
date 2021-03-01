import enum
import socket
import zmq
from .exceptions import ZebrokNotImplementedError


class SocketType(enum.Enum):
    """
    Type of socket connection to be established
    """

    ZmqPull = zmq.PULL
    ZmqPush = zmq.PUSH


class SocketHost(object):
    """
    Resolves hosts to ip addresses
    """

    @staticmethod
    def to_ip(host):
        return host if host == "*" else socket.gethostbyname(host)


class BaseSocketConnection(object):
    """
    All connection implementation must inherit from this base class
    """

    def __init__(self, socket_type, host, port, context):
        self.socket_type = socket_type.value
        self.host = SocketHost.to_ip(host)
        self.port = int(port)
        self.socket_address = self.get_socket_address()
        self.context = context
        self.socket = None

    def close(self):
        raise ZebrokNotImplementedError

    def get_socket_address(self):
        return f"tcp://{self.host}:{str(self.port)}"


class ZmqBindConnection(BaseSocketConnection):
    """
    Specialized 0mq socket binding implementation
    """

    def __init__(self, socket_type, host, port, context=None):
        if not context:
            context = zmq.Context()
        super().__init__(socket_type, host, port, context)
        self.socket = self.context.socket(self.socket_type)
        self.socket.bind(self.socket_address)

    def close(self):
        self.socket.close()
        self.context.term()


class ZmqConnectTypeConnection(BaseSocketConnection):
    """
    Specialized 0mq socket connection implementation
    """

    def __init__(self, socket_type, host, port, context=None):
        if not context:
            context = zmq.Context()
        super().__init__(socket_type, host, port, context)
        self.socket = self.context.socket(self.socket_type)
        self.socket.connect(self.socket_address)

    def close(self):
        self.socket.close()
        self.context.term()


class ConnectionType:
    """
    ConnectionFactory dependent class for determining
    which connection type to create
    """

    zmq_bind = ZmqBindConnection.__name__
    zmq_connect = ZmqConnectTypeConnection.__name__


class ConnectionFactory:
    """
    Factory class fo instantiating socket connections
    """

    @staticmethod
    def create_connection(connection_type, *args):
        connection = globals()[connection_type](*args)
        assert issubclass(
            type(connection), BaseSocketConnection
        ), "{} must inherit from {}".format(type(connection), str(BaseSocketConnection))
        return connection
