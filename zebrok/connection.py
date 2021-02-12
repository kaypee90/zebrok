import zmq
from .utils import get_socket_address_from_conf


class ZmqConnection(object):
    '''
    Handles message queue socket connections
    '''
    @classmethod
    def initialize(cls, bind_to_socket):
        context = zmq.Context()
        socket_address = get_socket_address_from_conf()
        if bind_to_socket:
            sock = cls._bind_to_socket(context, socket_address)
        else:
            sock = cls._connect_to_socket(context, socket_address)

        return sock, context
        

    @classmethod
    def _bind_to_socket(cls, context, socket_address):
        '''
        Binds the publisher to the socket connection
        '''
        sock = context.socket(zmq.PUSH)
        sock.bind(socket_address)
        return sock

    @classmethod
    def _connect_to_socket(cls, context, socket_address):
        '''
        Connects a worker to the socket connection
        '''
        sock = context.socket(zmq.PULL)
        sock.connect(socket_address)
        return sock


class SocketConnection(ZmqConnection):
    def __init__(self, bind=False):
        self.sock, self.context = super().initialize(bind)

    def __enter__(self):
        return self.sock

    def __exit__(self, type, value, traceback):
        self.sock.close()
        self.context.term()
