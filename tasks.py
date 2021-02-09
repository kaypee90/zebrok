from zebrok import app
import time


@app.Task
def long_running_task_one(firstname, lastname):
    '''
    An example task to emulate a long running task
    '''
    time.sleep(2)
    print(f"Hello, {firstname} {lastname}")
    time.sleep(2)
    print("DONE!!!")


@app.Task
def long_running_task_two(email):
    '''
    An example task to emulate a long running task
    '''
    time.sleep(2)
    print(f"Sent mail to, {email}")
    time.sleep(2)
    print("DONE!!!")
