# zebrok
![App workflow](https://github.com/kaypee90/zebrok/actions/workflows/python-app.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Brokerless task queue for python based on 0Mq

### - How to use zebrok
========================

* Configuring Environment Variables:
    - WORKER_HOST  &#160; &#160; &#160; &#160; # The IP address to expose running workers on
    - WORKER_PORT   &#160; &#160; &#160; &#160; &#160; &#160;  &#160;  # The port number workers should listen on

    -- `If not set defaults to localhost:5690`

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


### Running Zebrok examples with docker compose
* First clone the repository using the command `git clone git@github.com:kaypee90/zebrok.git`
* Change directory into the zebrok directory and run `docker compose up` command to start the worker and publisher containers.
* Access the shell for the **worker** container and run the command `python examples/start.py` to start the workers.
* From a different terminal window, access the shell for the running **publisher** container and run the command `python examples/client.py` to queue 2 jobs to be processed.
* Once these commands are executed you should see 2 tasks processed successfully in the publisher terminal.


**Sample output:**
```
** 2 ZEBROK TASKS DISCOVERED! 
=====================================================
  * long_running_task_one 
  * long_running_task_two 
=====================================================
2023-10-11 23:45:14,227 zebrok.discovery INFO:** 2 ZEBROK TASKS DISCOVERED! 
=====================================================
  * long_running_task_one 
  * long_running_task_two 
=====================================================
starting worker on: tcp://172.21.0.3:5691
2023-10-11 23:45:14,236 zebrok.worker INFO:starting worker on: tcp://172.21.0.3:5691
starting worker on: tcp://172.21.0.3:5692
2023-10-11 23:45:14,237 zebrok.worker INFO:starting worker on: tcp://172.21.0.3:5692
starting worker on: tcp://172.21.0.3:5693
starting worker on: tcp://172.21.0.3:5690
2023-10-11 23:45:14,238 zebrok.worker INFO:starting worker on: tcp://172.21.0.3:5693
2023-10-11 23:45:14,238 zebrok.worker INFO:starting worker on: tcp://172.21.0.3:5690
sending task to slave worker
2023-10-11 23:48:07,297 zebrok.worker INFO:sending task to slave worker
sending task to slave worker
received task: long_running_task_one
2023-10-11 23:48:07,299 zebrok.worker INFO:sending task to slave worker
2023-10-11 23:48:07,299 zebrok.worker INFO:received task: long_running_task_one
received task: long_running_task_two
2023-10-11 23:48:07,300 zebrok.worker INFO:received task: long_running_task_two
Sent mail to, samplemail@mail.com
Hello, Kay Pee
DONE!!!
DONE!!!
```


### Using a container orchestration technology (like Kubernetes):
- `number_of_slaves` must always be set to 0, then you can spin a number of replicas for the workers.
- `WORKER_HOST` Environment variable for a worker must always be `*`

