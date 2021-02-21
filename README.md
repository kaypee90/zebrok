# zebrok
Brokerless task queue for python based on 0Mq

### - How to use zebrok
========================

* Configuring Env Vars:
    - WORKER_HOST=
    - WORKER_PORT=

    -- `If not set defaults to localhost:5690`
    -- `WORKER_HOST env var for a worker on k8s must always be *`

* Creating A Task [tasks.py]
```
from zebrok import app

@app.Task
def long_running_task(param):
    do_some_time_consuming_task(param)
```

* Configuring a worker and registering the task [examples/start.py]
    - NB: `A task can also be discovered automatically if placed in a tasks.py file in the root folder of the project.`
    `- You can also set number of slave worker threads to be running by passing number_of_slaves argument`
```
from zebrok.worker import WorkerInitializer
from tasks import long_running_task


worker = WorkerInitializer(number_of_slaves=1, auto_discover=True)
worker.register_task(long_running_task)
worker.start()
```

* Starting the Zebrok Worker to listen for tasks -
`python examples/start.py` where start.py is the file in which you configured the worker

* Executing a task [examples/client.py]
```
from tasks import long_running_task

long_running_task.run(param="dowork")
```

- This library comes with the benefits of 0Mq
     - Low Latency
     - Lightweight
     - No broker required
     - Fast
     - Open source

# Todo
- Add k8s support for slave workers . Currently `number_of_slaves` must always be set to 0 on k8s

