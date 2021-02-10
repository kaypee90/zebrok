"""
Example startup file showing how zebrok worker can be configured
for an application
"""

from zebrok.worker import Worker
from tasks import long_running_task_two


worker = Worker(auto_discover=True)
worker.register(long_running_task_two)
worker.start()
