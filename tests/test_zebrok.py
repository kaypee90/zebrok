import asyncio
import json
import logging
import os
import socket
import sys
import threading
import time
import unittest
from unittest import mock

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import zebrok
from zebrok import app
from zebrok.connection import (
    ConnectionFactory,
    ConnectionType,
    SocketType,
    ZmqBindConnection,
    ZmqConnectTypeConnection,
)
from zebrok.discovery import discover_tasks, get_discovered_task_by_name
from zebrok.exceptions import ZebrokPublishError
from zebrok.logging import create_logger
from zebrok.registry import InMemoryTaskRegistry, RegistryFactory, RegistryType
from zebrok.task_runner import BaseTaskRunner, DefaultTaskRunner
from zebrok.utils import get_worker_port_and_host
from zebrok.worker import TaskQueueWorker, WorkerInitializer

CLEAN_ENV = {
    k: v
    for k, v in os.environ.items()
    if k not in ("WORKER_HOST", "WORKER_PORT") and not k.startswith("ZEBROK_")
}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def reset_zebrok_logger():
    """Removes zebrok's handlers so the next create_logger() reconfigures"""
    root = logging.getLogger("zebrok")
    for h in list(root.handlers):
        if getattr(h, "_zebrok", False):
            root.removeHandler(h)
            h.close()


class TestLoggingSetup(unittest.TestCase):
    def tearDown(self):
        reset_zebrok_logger()
        with mock.patch.dict(os.environ, CLEAN_ENV, clear=True):
            create_logger("zebrok.tests")

    def test_create_logger(self):
        logger = create_logger(__name__)
        self.assertIsNotNone(logger)

    def test_handlers_are_not_duplicated(self):
        create_logger("zebrok.tests.a")
        count = len(logging.getLogger("zebrok").handlers)
        child = create_logger("zebrok.tests.a")
        create_logger("zebrok.tests.b")
        self.assertEqual(count, len(logging.getLogger("zebrok").handlers))
        self.assertEqual([], child.handlers)  # handlers live on the parent only
        self.assertTrue(child.propagate)

    def test_no_log_file_by_default(self):
        reset_zebrok_logger()
        with mock.patch.dict(os.environ, CLEAN_ENV, clear=True):
            create_logger("zebrok.tests.nofile")
        self.assertFalse(
            any(
                isinstance(h, logging.FileHandler)
                for h in logging.getLogger("zebrok").handlers
            ),
        )

    def test_log_file_and_level_from_env(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "z.log")
            env = {"ZEBROK_LOG_FILE": path, "ZEBROK_LOG_LEVEL": "warning"}
            reset_zebrok_logger()
            with mock.patch.dict(os.environ, env):
                create_logger("zebrok.tests.withfile")
            parent = logging.getLogger("zebrok")
            self.assertEqual(logging.WARNING, parent.level)
            file_handlers = [
                h for h in parent.handlers if isinstance(h, logging.FileHandler)
            ]
            self.assertEqual(1, len(file_handlers))
            reset_zebrok_logger()

    def test_records_propagate_and_parent_level_applies(self):
        logger = create_logger("zebrok.tests.propagate")
        parent = logging.getLogger("zebrok")
        old_level = parent.level
        try:
            with self.assertLogs("zebrok", level="INFO") as captured:
                logger.info("visible")
            self.assertIn("visible", captured.output[0])
            parent.setLevel(logging.ERROR)
            self.assertFalse(logger.isEnabledFor(logging.INFO))
        finally:
            parent.setLevel(old_level)


class TestDefaultTaskRunner(unittest.TestCase):
    def setUp(self):
        def say_hello(name):
            print(f"Hello to you {name}")

        self.registry = {"say_hello": say_hello}

    def test_run_registered_task(self):
        runner = DefaultTaskRunner(self.registry, True)
        is_executed = runner.execute("say_hello", **{"name": "John"})
        self.assertTrue(is_executed)

    def test_run_non_registered_task(self):
        runner = DefaultTaskRunner(self.registry, True)
        is_executed = runner.execute("print_name", **{"name": "Sam"})
        self.assertFalse(is_executed)

    def test_positional_args(self):
        calls = []
        runner = DefaultTaskRunner({"add": lambda a, b: calls.append(a + b)})
        self.assertTrue(runner.execute("add", 2, b=3))
        self.assertEqual([5], calls)

    def test_failing_task_is_contained(self):
        def boom():
            raise RuntimeError("boom")

        runner = DefaultTaskRunner({"boom": boom})
        self.assertFalse(runner.execute("boom"))

    def test_retries(self):
        attempts = []

        def flaky():
            attempts.append(1)
            if len(attempts) < 3:
                raise RuntimeError("not yet")

        runner = DefaultTaskRunner({"flaky": flaky}, max_retries=2)
        self.assertTrue(runner.execute("flaky"))
        self.assertEqual(3, len(attempts))

    def test_retries_exhausted(self):
        attempts = []

        def always_fails():
            attempts.append(1)
            raise RuntimeError("nope")

        runner = DefaultTaskRunner({"f": always_fails}, max_retries=1)
        self.assertFalse(runner.execute("f"))
        self.assertEqual(2, len(attempts))

    def test_invalid_retry_settings(self):
        with self.assertRaises(ValueError):
            DefaultTaskRunner({}, max_retries=-1)
        with self.assertRaises(ValueError):
            DefaultTaskRunner({}, retry_delay=-1)

    def test_async_task(self):
        done = []

        @app.Task
        async def async_job(x):
            await asyncio.sleep(0)
            done.append(x)

        runner = DefaultTaskRunner({"async_job": async_job})
        self.assertTrue(runner.execute("async_job", 7))
        self.assertEqual([7], done)

    def test_discovery_refuses_non_task_callables(self):
        # tasks.py does `import time`; that must not be remotely callable.
        runner = DefaultTaskRunner({}, auto_discover=True)
        self.assertFalse(runner.execute("time"))


class TestConnectionFactory(unittest.TestCase):
    def test_create_zmq_connect_type(self):
        connection_type = ConnectionType.zmq_connect
        settings = (
            SocketType.ZmqPull,
            "localhost",
            7890,
        )
        connection = ConnectionFactory.create_connection(connection_type, *settings)
        self.assertIsInstance(connection, ZmqConnectTypeConnection)
        self.assertEqual(connection.socket_address, "tcp://127.0.0.1:7890")
        self.assertEqual(connection.socket_type, SocketType.ZmqPull.value)
        connection.close()
        self.assertTrue(connection.context.closed)

    def test_create_zmq_bind_type(self):
        connection_type = ConnectionType.zmq_bind
        settings = (
            SocketType.ZmqPush,
            "localhost",
            7891,
        )
        connection = ConnectionFactory.create_connection(connection_type, *settings)
        self.assertIsInstance(connection, ZmqBindConnection)
        self.assertEqual(connection.socket_address, "tcp://127.0.0.1:7891")
        self.assertEqual(connection.socket_type, SocketType.ZmqPush.value)
        connection.close()

    def test_shared_context_is_not_terminated(self):
        import zmq

        ctx = zmq.Context()
        connection = ConnectionFactory.create_connection(
            ConnectionType.zmq_bind,
            SocketType.ZmqPush,
            "localhost",
            0,
            ctx,
            address="inproc://shared-ctx-test",
        )
        self.assertEqual("inproc://shared-ctx-test", connection.socket_address)
        connection.close()
        self.assertFalse(ctx.closed)
        ctx.term()

    def test_unknown_connection_type(self):
        with self.assertRaises(ValueError):
            ConnectionFactory.create_connection("Nope", SocketType.ZmqPush, "x", 1)


class TestRegistryFactory(unittest.TestCase):
    def test_create_registry(self):
        in_memory_registry_type = RegistryType.in_memory
        registry = RegistryFactory.create_registry(in_memory_registry_type)
        self.assertIsInstance(registry, InMemoryTaskRegistry)

    def test_unknown_registry_type(self):
        with self.assertRaises(ValueError):
            RegistryFactory.create_registry("Nope")


class TestDiscovery(unittest.TestCase):
    def test_get_discovered_task_by_name(self):
        expected_discovered_task_name = "long_running_task_one"
        func = get_discovered_task_by_name(expected_discovered_task_name)
        actual_discovered_task_name = func.get_task_object().__name__
        self.assertEqual(expected_discovered_task_name, actual_discovered_task_name)

    def test_discover_tasks(self):
        number_of_tasks = discover_tasks()
        self.assertEqual(2, number_of_tasks)

    def test_non_task_attribute_is_not_returned(self):
        self.assertIsNone(get_discovered_task_by_name("time"))
        self.assertIsNone(get_discovered_task_by_name("does_not_exist"))

    def test_missing_tasks_module(self):
        with mock.patch.dict(os.environ, {"ZEBROK_TASKS_MODULE": "no_such_module_x"}):
            self.assertEqual(0, discover_tasks())
            self.assertIsNone(get_discovered_task_by_name("anything"))


class TestUtils(unittest.TestCase):
    def test_get_worker_port_and_host(self):
        with mock.patch.dict(os.environ, CLEAN_ENV, clear=True):
            port, host = get_worker_port_and_host()

        self.assertEqual(port, 5690)
        self.assertEqual(host, "localhost")


class TestInMemoryRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = InMemoryTaskRegistry()

        @app.Task
        def hello():
            print("Hello World")

        self.hello = hello
        self.registry.register(hello)

    def test_register_task(self):
        @app.Task
        def scream():
            print("HAAAAYY!!!")

        self.registry.register(scream)
        self.assertEqual(2, len(self.registry))
        self.assertEqual(scream, self.registry["scream"])

    def test_register_plain_function(self):
        def plain():
            return "ok"

        self.registry.register(plain)
        self.assertIsInstance(self.registry["plain"], app.Task)
        self.assertEqual("ok", self.registry["plain"]())

    def test_unregister_task(self):
        self.registry.unregister("hello")
        self.assertEqual(0, len(self.registry))
        with self.assertRaises(KeyError):
            self.registry["hello"]

    def test_unregister_by_task_object(self):
        self.registry.unregister(self.hello)
        self.assertEqual(0, len(self.registry))


class TaskRunnerForTesting(BaseTaskRunner):
    def __init__(self):
        self.calls = []
        self.called = threading.Event()

    def execute(self, task_name, *args, **kwargs):
        self.calls.append((task_name, args, kwargs))
        self.called.set()
        return True


class TestTask(unittest.TestCase):
    def setUp(self):
        @app.Task
        def hello(name):
            """Says hello"""
            print(f"Hello World, {name}")
            return name

        self.func = hello

    def test_callable_for_task(self):
        expected_name = "KayPee"
        actual_name = self.func(name=expected_name)
        self.assertEqual(expected_name, actual_name)

    def test_callable_with_positional_args(self):
        self.assertEqual("KayPee", self.func("KayPee"))

    def test_task_keeps_function_metadata(self):
        self.assertEqual("hello", self.func.__name__)
        self.assertEqual("hello", self.func.name)
        self.assertEqual("Says hello", self.func.__doc__)

    def test_get_task_object(self):
        expected_func_name = "hello"
        actual_func_name = self.func.get_task_object().__name__
        self.assertEqual(expected_func_name, actual_func_name)

    def test_task_requires_callable(self):
        with self.assertRaises(TypeError):
            app.Task("not callable")

    def test_payload_includes_args(self):
        payload = json.loads(app.build_payload(self.func, ("a",), {"b": 1}))
        self.assertEqual({"task": "hello", "args": ["a"], "kwargs": {"b": 1}}, payload)

    def test_run_rejects_unserializable_args(self):
        with self.assertRaises(TypeError):
            self.func.run(object())

    def test_run_without_worker_fails_fast(self):
        env = {"WORKER_PORT": str(free_port()), "ZEBROK_PUBLISH_TIMEOUT_MS": "300"}
        with mock.patch.dict(os.environ, env):
            started = time.monotonic()
            with self.assertRaises(ZebrokPublishError):
                self.func.run("nobody listening")
            self.assertLess(time.monotonic() - started, 3)

    def test_arun_without_worker_fails_fast(self):
        env = {"WORKER_PORT": str(free_port()), "ZEBROK_PUBLISH_TIMEOUT_MS": "300"}
        with mock.patch.dict(os.environ, env):
            with self.assertRaises(ZebrokPublishError):
                asyncio.run(self.func.arun("nobody listening"))

    def test_package_exports(self):
        self.assertIs(zebrok.Task, app.Task)
        self.assertTrue(zebrok.__version__)


class TestWorkerInitializer(unittest.TestCase):
    def test_runner_is_cached(self):
        worker = WorkerInitializer()
        self.assertIs(worker.runner, worker.runner)

    def test_custom_runner_type_checked(self):
        worker = WorkerInitializer()
        with self.assertRaises(TypeError):
            worker.runner = object()
        custom = TaskRunnerForTesting()
        worker.runner = custom
        self.assertIs(custom, worker.runner)

    def test_invalid_number_of_slaves(self):
        with self.assertRaises(ValueError):
            WorkerInitializer(number_of_slaves=-1)

    def test_stop_when_not_started_is_noop(self):
        WorkerInitializer().stop()


class TestValidationAndCompat(unittest.TestCase):
    def test_publish_timeout_must_be_positive(self):
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                app.TaskPublisher(timeout_ms=bad)
            with self.assertRaises(ValueError):
                app.AsyncTaskPublisher(timeout_ms=bad)
        with mock.patch.dict(os.environ, {"ZEBROK_PUBLISH_TIMEOUT_MS": "0"}):
            with self.assertRaises(ValueError):
                app.TaskPublisher()

    def test_retry_settings_validated_early(self):
        with self.assertRaises(ValueError):
            WorkerInitializer(max_retries=-1)
        with self.assertRaises(ValueError):
            WorkerInitializer(retry_delay=-0.5)

    def test_task_subclass_overriding_get_task_object(self):
        def target():
            return "ok"

        class LegacyTask(app.Task):
            def __init__(self):  # does not call super().__init__
                pass

            def get_task_object(self):
                return target

        registry = InMemoryTaskRegistry()
        registry.register(LegacyTask)
        self.assertIn("target", registry)
        payload = json.loads(app.build_payload(LegacyTask(), (), {}))
        self.assertEqual("target", payload["task"])

    def test_legacy_connection_subclass(self):
        import zmq

        class LegacyConnection(ZmqBindConnection.__mro__[1]):  # BaseSocketConnection
            def __init__(self, socket_type, host, port, context=None):
                super().__init__(socket_type, host, port, context)
                self.socket = self.context.socket(self.socket_type)
                self.socket.bind(self.socket_address)

        port = free_port()
        connection = LegacyConnection(SocketType.ZmqPull, "127.0.0.1", port)
        self.assertEqual(zmq.PULL, connection.socket.type)
        connection.close()

    def test_dotted_missing_tasks_module(self):
        with mock.patch.dict(os.environ, {"ZEBROK_TASKS_MODULE": "nopkg_x.tasks"}):
            self.assertEqual(0, discover_tasks())


class TestEndToEnd(unittest.TestCase):
    """
    Starts real workers on a free port and publishes tasks to them
    """

    def setUp(self):
        self.env = mock.patch.dict(
            os.environ,
            {"WORKER_HOST": "127.0.0.1", "WORKER_PORT": str(free_port())},
        )
        self.env.start()
        self.received = []
        self.lock = threading.Lock()
        self.all_done = threading.Event()
        self.expected = 0

    def tearDown(self):
        self.env.stop()

    def _make_task(self):
        test = self

        @app.Task
        def record(a, b=0):
            with test.lock:
                test.received.append((a, b, threading.current_thread().name))
                if len(test.received) >= test.expected:
                    test.all_done.set()

        return record

    def _run(self, number_of_slaves, calls):
        record = self._make_task()
        self.expected = len(calls)
        worker = WorkerInitializer(number_of_slaves=number_of_slaves)
        worker.register_task(record)
        worker.start(block=False)
        try:
            for args, kwargs in calls:
                self.assertTrue(record.run(*args, **kwargs))
            self.assertTrue(self.all_done.wait(5), f"received only {self.received}")
        finally:
            started = time.monotonic()
            worker.stop(timeout=5)
            self.assertLess(time.monotonic() - started, 3)
            self.assertFalse(worker.is_running)
        return worker

    def test_master_only(self):
        self._run(0, [((1,), {"b": 2}), ((3,), {})])
        self.assertEqual({(1, 2), (3, 0)}, {(a, b) for a, b, _ in self.received})

    def test_with_slaves_round_robin(self):
        self._run(2, [((i,), {}) for i in range(4)])
        self.assertEqual({0, 1, 2, 3}, {a for a, _, _ in self.received})
        threads = {name for _, _, name in self.received}
        self.assertEqual({"zebrok-slave-0", "zebrok-slave-1"}, threads)

    def test_async_publish(self):
        record = self._make_task()
        self.expected = 1
        worker = WorkerInitializer()
        worker.register_task(record)
        worker.start(block=False)
        try:
            self.assertTrue(asyncio.run(record.arun(5, b=6)))
            self.assertTrue(self.all_done.wait(5))
            self.assertEqual((5, 6), self.received[0][:2])
        finally:
            worker.stop(timeout=5)

    def test_worker_survives_bad_messages_and_failing_tasks(self):
        record = self._make_task()

        @app.Task
        def explode():
            raise RuntimeError("boom")

        self.expected = 1
        worker = WorkerInitializer()
        worker.register_task(record)
        worker.register_task(explode)
        worker.start(block=False)
        try:
            import zmq

            port, host = get_worker_port_and_host()
            ctx = zmq.Context()
            push = ctx.socket(zmq.PUSH)
            push.connect(f"tcp://{host}:{port}")
            push.send(b"not json")
            push.send(b'{"no_task": 1}')
            push.send(b'{"task": "record", "args": "not-a-list"}')
            push.close(linger=1000)
            ctx.term()
            explode.run()
            record.run(42)
            self.assertTrue(self.all_done.wait(5))
            self.assertEqual(42, self.received[0][0])
        finally:
            worker.stop(timeout=5)

    def test_custom_runner_receives_args(self):
        @app.Task
        def hello(name):
            pass

        custom = TaskRunnerForTesting()
        worker = WorkerInitializer()
        worker.runner = custom
        worker.start(block=False)
        try:
            hello.run("King", greeting="Pee")
            self.assertTrue(custom.called.wait(5))
            self.assertEqual(("hello", ("King",), {"greeting": "Pee"}), custom.calls[0])
        finally:
            worker.stop(timeout=5)

    def test_cannot_start_twice(self):
        worker = WorkerInitializer()
        worker.start(block=False)
        try:
            with self.assertRaises(RuntimeError):
                worker.start(block=False)
        finally:
            worker.stop(timeout=5)

    def test_blocking_start_stops_on_keyboard_interrupt(self):
        worker = WorkerInitializer(number_of_slaves=1)
        original = TaskQueueWorker.start
        calls = {"n": 0}

        def interrupting_start(self_):
            calls["n"] += 1
            if self_ is worker._master:
                raise KeyboardInterrupt
            original(self_)

        with mock.patch.object(TaskQueueWorker, "start", interrupting_start):
            worker.start()  # must return instead of hanging
        self.assertFalse(worker.is_running)

    def test_port_in_use_cleans_up(self):
        port, _ = get_worker_port_and_host()
        blocker = WorkerInitializer()
        blocker.start(block=False)
        try:
            other = WorkerInitializer(number_of_slaves=1)
            with self.assertRaises(Exception):
                other.start(block=False)
            self.assertFalse(other.is_running)
        finally:
            blocker.stop(timeout=5)

    def test_cross_thread_stop_during_blocking_start(self):
        worker = WorkerInitializer(number_of_slaves=1)
        thread = threading.Thread(target=worker.start)  # blocking start
        thread.start()
        deadline = time.monotonic() + 5
        while not worker.is_running and time.monotonic() < deadline:
            time.sleep(0.01)
        worker.stop()
        thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertFalse(worker.is_running)

    def test_restart_after_stop(self):
        record = self._make_task()
        worker = WorkerInitializer(number_of_slaves=1)
        worker.register_task(record)
        for i in range(2):
            self.all_done.clear()
            self.expected = i + 1
            worker.start(block=False)
            try:
                record.run(i)
                self.assertTrue(self.all_done.wait(5))
            finally:
                worker.stop(timeout=5)
        self.assertEqual([0, 1], [a for a, _, _ in self.received])

    def test_stop_waits_for_running_task(self):
        started, finished = threading.Event(), threading.Event()

        @app.Task
        def slow():
            started.set()
            time.sleep(0.5)
            finished.set()

        for slaves in (0, 1):
            started.clear()
            finished.clear()
            worker = WorkerInitializer(number_of_slaves=slaves)
            worker.register_task(slow)
            worker.start(block=False)
            slow.run()
            self.assertTrue(started.wait(5))
            worker.stop(timeout=5)
            self.assertTrue(finished.is_set())

    def test_task_calling_sys_exit_does_not_kill_slave(self):
        record = self._make_task()

        @app.Task
        def quitter():
            sys.exit(3)

        self.expected = 2
        worker = WorkerInitializer(number_of_slaves=1)
        worker.register_task(record)
        worker.register_task(quitter)
        worker.start(block=False)
        try:
            quitter.run()
            record.run(1)
            quitter.run()
            record.run(2)
            self.assertTrue(self.all_done.wait(5), f"received only {self.received}")
        finally:
            started = time.monotonic()
            worker.stop(timeout=5)
            self.assertLess(time.monotonic() - started, 3)

    def test_auto_discover_end_to_end_refuses_non_tasks(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "called")
            module_name = "zebrok_e2e_tasks"
            with open(os.path.join(tmp, module_name + ".py"), "w") as f:
                f.write(
                    "from zebrok import Task\n"
                    f"MARKER = {marker!r}\n"
                    "def touch(path):  # NOT a task\n"
                    "    open(path, 'w').close()\n"
                    "@Task\n"
                    "def write_marker(suffix):\n"
                    "    open(MARKER + suffix, 'w').close()\n",
                )
            sys.path.insert(0, tmp)
            try:
                with mock.patch.dict(os.environ, {"ZEBROK_TASKS_MODULE": module_name}):
                    worker = WorkerInitializer(auto_discover=True)
                    worker.start(block=False)
                    try:
                        from zebrok.app import TaskPublisher

                        with TaskPublisher() as publisher:
                            # name only; "touch" is a plain function
                            publisher.publish_task(
                                type("F", (), {"__name__": "touch"}),
                                marker,
                            )
                        import importlib

                        mod = importlib.import_module(module_name)
                        mod.write_marker.run(".ok")
                        deadline = time.monotonic() + 5
                        while not os.path.exists(marker + ".ok"):
                            self.assertLess(time.monotonic(), deadline)
                            time.sleep(0.02)
                    finally:
                        worker.stop(timeout=5)
                self.assertFalse(os.path.exists(marker))
            finally:
                sys.path.remove(tmp)
                sys.modules.pop(module_name, None)


SUBPROCESS_PRELUDE = """
import os, sys, threading, time
sys.path.insert(0, {repo!r})
os.environ["WORKER_HOST"] = "127.0.0.1"
os.environ["WORKER_PORT"] = {port!r}
from zebrok import Task, WorkerInitializer
"""


class TestProcessLevel(unittest.TestCase):
    """
    Scenarios that involve real signals or that used to abort the
    interpreter, run in a subprocess so a regression can't kill the suite
    """

    repo = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    def run_script(self, body, timeout=20):
        import subprocess

        code = SUBPROCESS_PRELUDE.format(repo=self.repo, port=str(free_port())) + body
        return subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def test_concurrent_stop_calls(self):
        result = self.run_script(
            """
for _ in range(20):
    w = WorkerInitializer(number_of_slaves=2)
    w.start(block=False)
    ts = [threading.Thread(target=w.stop) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    deadline = time.monotonic() + 5
    while w._stopping and time.monotonic() < deadline:
        time.sleep(0.01)
print("OK")
""",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("OK", result.stdout)

    def _graceful_signal(self, sig, slaves):
        import signal
        import subprocess

        port = str(free_port())
        code = SUBPROCESS_PRELUDE.format(repo=self.repo, port=port) + f"""
@Task
def slow():
    print("task start", flush=True)
    time.sleep(1)
    print("task end", flush=True)

w = WorkerInitializer(number_of_slaves={slaves})
w.register_task(slow)
threading.Thread(target=lambda: (time.sleep(0.5), slow.run())).start()
w.start()
print("returned", flush=True)
"""
        proc = subprocess.Popen(
            [sys.executable, "-c", code],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL),
        )
        try:
            line = ""
            while "task start" not in line:
                line = proc.stdout.readline()
                self.assertTrue(line, "worker exited early")
            proc.send_signal(sig)
            out, _ = proc.communicate(timeout=10)
        finally:
            if proc.poll() is None:
                proc.kill()
        self.assertEqual(0, proc.returncode, out)
        self.assertIn("task end", out)
        self.assertIn("returned", out)

    def test_sigterm_is_graceful(self):
        import signal

        for slaves in (0, 2):
            self._graceful_signal(signal.SIGTERM, slaves)

    def test_ctrl_c_is_graceful(self):
        import signal

        for slaves in (0, 2):
            self._graceful_signal(signal.SIGINT, slaves)


if __name__ == "__main__":
    unittest.main()
