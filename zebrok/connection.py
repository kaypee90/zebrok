import zmq
from .utils import get_socket_address_from_conf


class SocketConnection(object):
    @staticmethod
    def bind_to_socket():
        context = zmq.Context()
        sock = context.socket(zmq.PUSH)
        socket_address = get_socket_address_from_conf()
        sock.bind(socket_address)
        return sock

    @staticmethod
    def connect_to_socket():
        context = zmq.Context()
        sock = context.socket(zmq.PULL)
        socket_address = get_socket_address_from_conf(worker=True)
        sock.connect(socket_address)
        return sock
