# zebrok
Brokerless task queue for python based on 0Mq

### - How to use zebrok
========================

* Configuring Env Vars:
    - PUBLISHER_HOST=
    - PUBLISHER_PORT=

    -- `If not set defaults to localhost:5690`

* Creating A Task [tasks.py]
```
from zebrok import app

@app.Task
def long_running_task(param):
    do_some_time_consuming_task(param)
```

* Configuring a worker and registering the task [start.py]
    - NB: `A task can also be discovered automatically if placed in a tasks.py file in the root folder of the project.`
```
from zebrok.worker import Worker
from tasks import long_running_task


worker = Worker(auto_discover=True)
worker.register(long_running_task)
worker.start()
```

* Starting the Zebrok Worker to listen for tasks -
`python start.py` where start.py is the file in which you configured the worker

* Executing a task [client.py]
```
from tasks import long_running_task

long_running_task_one.run(param="dowork")
```

- This library comes with the benefits of 0Mq
     - Low Latency
     - Lightweight
     - No broker required
     - Fast
     - Open source
