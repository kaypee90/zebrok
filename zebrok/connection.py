import enum
import socket
import zmq


class SocketType(enum.Enum):
    ZmqPull = zmq.PULL
    ZmqPush = zmq.PUSH


class SocketHost(object):
    @staticmethod
    def to_ip(host):
        return host if host == "*" else socket.gethostbyname(host)


class BaseSocketConnection(object):
    def __init__(self, socket_type, host, port, context):
        self.socket_type = socket_type.value
        self.host = SocketHost.to_ip(host)
        self.port = int(port)
        self.socket_address = self.get_socket_address()
        self.context = context
        self.socket = None

    def close(self):
        raise NotImplementedError

    def get_socket_address(self):
        return f"tcp://{self.host}:{str(self.port)}"


class ZmqBindConnection(BaseSocketConnection):
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
    def __init__(self, socket_type, host, port, context=None):
        if not context:
            context = zmq.Context()
        super().__init__(socket_type, host, port, context)
        self.socket = self.context.socket(self.socket_type)
        self.socket.connect(self.socket_address)

    def close(self):
        self.socket.close()
        self.context.term()
