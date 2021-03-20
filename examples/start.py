"""
Example startup file showing how zebrok worker can be configured
for an application
"""
import examples
from zebrok.worker import WorkerInitializer
from tasks import long_running_task_two


worker = WorkerInitializer(number_of_slaves=0, auto_discover=True)
worker.register_task(long_running_task_two)
worker.start()
