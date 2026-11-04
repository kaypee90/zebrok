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
2026-11-03 20:09:59 - zebrok.discovery - INFO - ** 2 ZEBROK TASKS DISCOVERED!
=====================================================
  * long_running_task_one
  * long_running_task_two
=====================================================
2026-11-03 20:09:59 - zebrok.worker - INFO - starting worker on: inproc://zebrok-4343030624-slave-0
2026-11-03 20:09:59 - zebrok.worker - INFO - starting worker on: inproc://zebrok-4343030624-slave-1
2026-11-03 20:09:59 - zebrok.worker - INFO - starting worker on: inproc://zebrok-4343030624-slave-2
2026-11-03 20:09:59 - zebrok.worker - INFO - starting worker on: tcp://172.21.0.3:5690
2026-11-03 20:10:00 - zebrok.worker - INFO - received task: long_running_task_one
2026-11-03 20:10:00 - zebrok.worker - INFO - received task: long_running_task_two
Hello, Kay Pee
Sent mail to, samplemail@mail.com
DONE!!!
DONE!!!
```

Press `Ctrl+C` (or send `SIGTERM`, as `docker stop` does) to stop the worker.
Tasks that are already running finish first (press `Ctrl+C` a second time to force an immediate exit);
tasks still waiting in the queue are dropped.

## Trying out zebrok

1. **Install Zebrok** (Python 3.10+)
```sh
   pip install git+https://github.com/kaypee90/zebrok.git#egg=zebrok
```

2. **Configuring Environment Variables:**

| Variable | Default | Purpose |
|---|---|---|
| `WORKER_HOST` | `localhost` | IP address / host name the worker listens on and publishers connect to (`*` = all interfaces, for workers only) |
| `WORKER_PORT` | `5690` | Port the worker listens on |
| `ZEBROK_PUBLISH_TIMEOUT_MS` | `5000` | How long `run()` waits to reach a worker before raising `ZebrokPublishError` |
| `ZEBROK_TASKS_MODULE` | `tasks` | Module scanned when `auto_discover=True` |
| `ZEBROK_LOG_LEVEL` | `INFO` | Log level for zebrok's loggers |
| `ZEBROK_LOG_FILE` | *(unset)* | Also write logs to this file. By default logs go to the console only |

Zebrok logs through the standard `logging` module under the `zebrok` logger. Until your application
configures logging, zebrok prints its own logs to the console; once you do (e.g. `logging.basicConfig()`),
its records go to your handlers instead, and `logging.getLogger("zebrok").setLevel(...)` controls them.

3. **Creating a Task `(tasks.py)`**
```python
from zebrok import Task

@Task
def long_running_task(param, retries=1):
    do_some_time_consuming_task(param, retries)


@Task
async def async_task(url):  # async functions are supported too
    await fetch(url)
```

4. **Configuring a Worker and Registering the Task (examples/start.py):**
    - NB: `A task can also be discovered automatically if placed in a tasks.py file in the root folder of the project.`
      Only functions decorated with `@Task` can be run by a worker.
    - `number_of_slaves` sets how many worker threads the main worker hands tasks to (round robin).
    - `max_retries` / `retry_delay` retry a task that raises an exception.
```python
from zebrok import WorkerInitializer
from tasks import long_running_task


worker = WorkerInitializer(number_of_slaves=1, auto_discover=True, max_retries=2)
worker.register_task(long_running_task)
worker.start()  # blocks until Ctrl+C / SIGTERM
```
   To run the worker in the background of another program, use
   `worker.start(block=False)` and call `worker.stop()` to shut it down.

5. **Starting the Zebrok Worker:**
  where **start.py** is the file in which you configured the worker
  ```sh
   python examples/start.py
  ```

6. **Executing a task (`examples/client.py`)**
```python
from tasks import long_running_task

long_running_task.run("dowork", retries=3)  # positional and keyword arguments
```
   Arguments must be JSON serializable. If no worker can be reached within
   `ZEBROK_PUBLISH_TIMEOUT_MS`, `run()` raises `zebrok.ZebrokPublishError`
   instead of hanging.

   From async code (FastAPI, aiohttp, ...) use `arun`, which does not block the event loop:
```python
await long_running_task.arun("dowork")
```

[Link to sample fastapi project using Zebrok](https://github.com/kaypee90/sample-zebrok-1)


### Using a container orchestration technology (like Kubernetes):
- Set `number_of_slaves` to 0, then spin up multiple replicas for the workers.
- The `WORKER_HOST` environment variable for a worker must be set `*`
- Workers stop gracefully on `SIGTERM`, so rolling updates let running tasks finish.

### Docker image
The image (`kaypee90/zebrok`) is built from the `Dockerfile` and published to Docker Hub by the
`Docker image` GitHub workflow whenever a `v*` tag is pushed. The workflow needs the
`DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` repository secrets.
