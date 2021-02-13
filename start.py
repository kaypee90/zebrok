"""
Example startup file showing how zebrok worker can be configured
for an application
"""

from zebrok.worker import Worker
from tasks import long_running_task_two


worker = Worker(number_of_slaves=5, auto_discover=True)
worker.register_task(long_running_task_two)
worker.start()
