import asyncio
import functools
import json
from collections.abc import Callable
from types import TracebackType
from typing import Any

import zmq
import zmq.asyncio

from .connection import ConnectionFactory, ConnectionType, SocketType
from .exceptions import ZebrokPublishError
from .utils import (
    get_publish_timeout_ms,
    get_worker_port_and_host,
    validate_timeout_ms,
)


def _task_name(task: Any) -> str:
    """
    Returns the name a task is registered and published under
    """
    return task.name if isinstance(task, Task) else task.__name__


def build_payload(task: Any, args: tuple, kwargs: dict) -> bytes:
    """
    Serializes a task call into the wire format understood by workers.

    Raises:
        TypeError: if the arguments cannot be serialized to JSON
    """
    payload = {"task": _task_name(task), "args": list(args), "kwargs": kwargs}
    try:
        return json.dumps(payload).encode("utf-8")
    except (TypeError, ValueError) as e:
        raise TypeError(
            f"Arguments for task '{payload['task']}' must be JSON serializable: {e}",
        ) from e


def _no_worker_error(address: str, timeout_ms: int) -> ZebrokPublishError:
    return ZebrokPublishError(
        f"Could not deliver task to a worker at {address} within {timeout_ms}ms. "
        "Is a worker running?",
    )


class TaskPublisher:
    """
    Handles pushing of tasks to task queue
    """

    def __init__(self, timeout_ms: int | None = None) -> None:
        """
        parameters:
            timeout_ms (int): how long to wait for a worker to accept the
                task before raising ZebrokPublishError. Defaults to
                ZEBROK_PUBLISH_TIMEOUT_MS (5000)
        """
        port, host = get_worker_port_and_host()
        self.timeout_ms = (
            get_publish_timeout_ms()
            if timeout_ms is None
            else validate_timeout_ms(timeout_ms)
        )
        self.connection = ConnectionFactory.create_connection(
            ConnectionType.zmq_connect,
            SocketType.ZmqPush,
            host,
            port,
            # Only queue messages once a worker is actually connected, and
            # give up after the timeout instead of blocking forever.
            socket_options={zmq.IMMEDIATE: 1, zmq.SNDTIMEO: self.timeout_ms},
        )
        self.socket = self.connection.socket

    def __enter__(self) -> "TaskPublisher":  # noqa: PYI034 (typing.Self is 3.11+)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """
        Closes the connection, waiting at most timeout_ms for queued
        messages to be flushed to the worker
        """
        self.connection.close(linger=self.timeout_ms)

    def publish_task(self, task: Callable[..., Any], *args: Any, **kwargs: Any) -> bool:
        """
        Sends a task to a worker

        Raises:
            TypeError: if the arguments are not JSON serializable
            ZebrokPublishError: if no worker accepted the task in time
        """
        data = build_payload(task, args, kwargs)
        try:
            self.socket.send(data)
        except zmq.Again as e:
            raise _no_worker_error(
                self.connection.socket_address, self.timeout_ms
            ) from e
        return True


class AsyncTaskPublisher:
    """
    asyncio variant of TaskPublisher, built on zmq.asyncio.
    Use it from async code (FastAPI, aiohttp, ...) so publishing
    never blocks the event loop.
    """

    def __init__(self, timeout_ms: int | None = None) -> None:
        port, host = get_worker_port_and_host()
        self.timeout_ms = (
            get_publish_timeout_ms()
            if timeout_ms is None
            else validate_timeout_ms(timeout_ms)
        )
        context = zmq.asyncio.Context()
        try:
            self.connection = ConnectionFactory.create_connection(
                ConnectionType.zmq_connect,
                SocketType.ZmqPush,
                host,
                port,
                context,
                socket_options={zmq.IMMEDIATE: 1},
            )
        except Exception:
            context.term()
            raise
        self.socket = self.connection.socket

    async def __aenter__(self) -> "AsyncTaskPublisher":  # noqa: PYI034
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """
        Closes the socket and terminates its context. Terminating may wait up
        to timeout_ms for queued messages, so it runs in a thread to keep the
        event loop responsive.
        """
        if not self.socket.closed:
            self.socket.close(linger=self.timeout_ms)
        context = self.connection.context
        if not context.closed:
            await asyncio.get_running_loop().run_in_executor(None, context.term)

    async def publish_task(
        self,
        task: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """
        Sends a task to a worker without blocking the event loop

        Raises:
            TypeError: if the arguments are not JSON serializable
            ZebrokPublishError: if no worker accepted the task in time
        """
        data = build_payload(task, args, kwargs)
        try:
            await asyncio.wait_for(self.socket.send(data), self.timeout_ms / 1000)
        except asyncio.TimeoutError as e:
            raise _no_worker_error(
                self.connection.socket_address, self.timeout_ms
            ) from e
        return True


class Task:
    """
    Extends the methods to be used with task queue.

    Calling the task directly runs it in the current process;
    use run() / arun() to send it to a worker instead.
    """

    def __init__(self, arg: Callable[..., Any]) -> None:
        if not callable(arg):
            raise TypeError(f"Task expects a callable, got {type(arg).__name__}")
        self._arg = arg
        functools.update_wrapper(self, arg)

    @property
    def name(self) -> str:
        """
        Name the task is registered and published under
        """
        return self.get_task_object().__name__

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._arg(*args, **kwargs)

    def get_task_object(self) -> Callable[..., Any]:
        return self._arg

    def run(self, *args: Any, **kwargs: Any) -> bool:
        """
        Sends the task to a worker

        Raises:
            TypeError: if the arguments are not JSON serializable
            ZebrokPublishError: if no worker accepted the task in time
        """
        build_payload(self, args, kwargs)  # fail fast before opening a socket
        with TaskPublisher() as publisher:
            return publisher.publish_task(self, *args, **kwargs)

    async def arun(self, *args: Any, **kwargs: Any) -> bool:
        """
        Sends the task to a worker from async code
        """
        build_payload(self, args, kwargs)
        async with AsyncTaskPublisher() as publisher:
            return await publisher.publish_task(self, *args, **kwargs)
