from zebrok.worker import Worker
from tasks import greet

worker = Worker()
worker.register(greet)
worker.start()