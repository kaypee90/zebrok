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


def convert_hostname_to_ip(hostname):
    """
    Converts host name to an ip address

    Parameters:
        hostname (str): name of host 

    Returns:
        str : converted ip address for host
    """
    return hostname if hostname == "*" else socket.gethostbyname(host)


class BaseSocketConnection(object):
    """
    All connection implementation must inherit from this base class

    socket_type = type of connection created by factory
    host = name of the host on which connection is being created
    port = socket connection port
    socket_address = tcp address for establishing the connection
    context = current connection context
    socket =  created socket connectio
    """

    def __init__(self, socket_type, host, port, context):
        self.socket_type = socket_type.value
        self.host = convert_hostname_to_ip(host)
        self.port = int(port)
        self.socket_address = self.get_socket_address()
        self.context = context
        self.socket = None

    def close(self):
        """
        Closes opened underlying socket connection
        """
        raise ZebrokNotImplementedError

    def get_socket_address(self):
        """
        Constructs tcp adddress to be connected to
        """
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
        """
        Creates sockect connections

        parameters:
            connection_type (str): Type of connection to create

        Returns:
            BaseSocketConnection : created socket connection
        """
        connection = globals()[connection_type](*args)
        assert issubclass(
            type(connection), BaseSocketConnection
        ), "{} must inherit from {}".format(type(connection), str(BaseSocketConnection))
        return connection
