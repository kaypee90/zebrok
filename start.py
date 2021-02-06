from zebrok.worker import Worker
from tasks import greet

worker = Worker(auto_discover=True)
# worker.register(greet)
worker.start()
