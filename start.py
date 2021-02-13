"""
Example startup file showing how zebrok worker can be configured
for an application
"""

from zebrok.worker import WorkerInitializer
from tasks import long_running_task_two


worker = WorkerInitializer(number_of_slaves=2, auto_discover=True)
worker.register_task(long_running_task_two)
worker.start()
