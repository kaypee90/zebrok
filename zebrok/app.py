from .connection import SocketConnection
from .utils import pickle_task

class Task(object):
    '''
    Extends methods to be used with task queue
    '''
    def __init__(self, arg):
	    self._arg = arg

    def __call__(self, *args, **kwargs):
        return self._arg(**kwargs)

    def get_task_object(self):
        return self._arg

    def run(self, *args, **kwargs):
        task =  {
            "task": self._arg.__name__, 
            "kwargs": kwargs 
        }
        payload = pickle_task(task)
        return self.__publish_task(payload)

    @classmethod
    def __publish_task(cls, task_payload):
        sock = SocketConnection.bind_to_socket()  
        sock.send_string(task_payload)
        return True

