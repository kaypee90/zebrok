import zmq
import json
from connection import SocketConnection
from utils import unpickle_task
from registry import TaskRegistry


class Worker(object):
    tasks = TaskRegistry()

    def register(self, task):
        self.tasks.register(task)

    def start(self):
        sock = SocketConnection().connect_to_socket()

        while True:
            message = sock.recv()
            payload = unpickle_task(message)
            func = self.tasks.get(payload["task"])
            kwargs = payload["kwargs"]
            func(**kwargs)