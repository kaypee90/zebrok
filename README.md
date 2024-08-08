# zebrok
![App workflow](https://github.com/kaypee90/zebrok/actions/workflows/python-app.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Brokerless task queue for Python based on ZeroMQ**

## Key Benefits of Using ZeroMQ
- **Fast:** High-performance messaging library.
- **Lightweight:** Minimal resource usage.
- **Open Source:** Free to use and modify.
- **Low Latency:** Efficient message passing.
- **No Broker Required:** Direct communication between endpoints.

## Running Zebrok Examples with Docker Compose
1. **Clone the repository:**  
   ```sh
   git clone git@github.com:kaypee90/zebrok.git
   ```

2. **Navigate to the Zebrok directory:**  
   ```sh
   cd zebrok
   ```

3. **Start the worker and publisher containers:**  
   ```sh
   docker-compose up
   ```

4. **Start the workers:**
   * Access the shell for the worker container:
   ```sh
   docker exec -it <worker-container-id> /bin/sh
   ```
   * Run the start script:
   ```sh
   python examples/start.py
   ```

5. **Queue jobs from the publisher:**
   * Access the shell for the publisher container from a different terminal:
   ```sh
   docker exec -it <publisher-container-id> /bin/sh
   ```
   * Queue jobs:
   ```sh
   python examples/client.py
   ```

6. **Expected Output:**

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

## Trying out zebrok

1. **Install Zebrok**
```sh
   pip install git+https://github.com/kaypee90/zebrok.git#egg=zebrok
```

2. **Configuring Environment Variables:**
    - `WORKER_HOST: The IP address for running workers (default: localhost)
    - `WORKER_PORT: The port number workers should listen on (default: 5690)

3. **Creating a Task `(tasks.py)`**
```
from zebrok import app

@app.Task
def long_running_task(param):
    do_some_time_consuming_task(param)
```

4. **Configuring a Worker and Registering the Task (examples/start.py):**
    - NB: `A task can also be discovered automatically if placed in a tasks.py file in the root folder of the project.`
    `- You can also set number of slave worker threads to be running by passing number_of_slaves argument`
```
from zebrok.worker import WorkerInitializer
from tasks import long_running_task


worker = WorkerInitializer(number_of_slaves=1, auto_discover=True)
worker.register_task(long_running_task)
worker.start()
```

5. **Starting the Zebrok Worker:**
  where **start.py** is the file in which you configured the worker
  ```sh
   python examples/start.py
  ```

6. **Executing a task (`examples/client.py`)**
```
from tasks import long_running_task

long_running_task.run(param="dowork")
```

[Link to sample fastapi project using Zebrok](https://github.com/kaypee90/sample-zebrok-1)


### Using a container orchestration technology (like Kubernetes):
- Set `number_of_slaves` to 0, then spin up multiple replicas for the workers.
- The `WORKER_HOST` environment variable for a worker must be set `*`
