"""
Example file showing how a registered task
can be called and executed on a zebrok worker
"""
import examples
from tasks import long_running_task_one, long_running_task_two

long_running_task_one.run(firstname="Kay", lastname="Pee")
long_running_task_two.run(email="samplemail@mail.com")
