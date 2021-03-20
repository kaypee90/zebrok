import os
import sys
import io
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from zebrok.utils import get_worker_port_and_host
from zebrok.registry import InMemoryTaskRegistry, RegistryFactory, RegistryType
from zebrok import app
from zebrok.task_runner import DefaultTaskRunner, BaseTaskRunner
from zebrok.worker import WorkerInitializer
from zebrok.logging import create_logger
from zebrok.discovery import get_discovered_task_by_name, discover_tasks
from zebrok.connection import (
    ConnectionType,
    ConnectionFactory,
    ZmqConnectTypeConnection,
    ZmqBindConnection,
    SocketType,
)


class TestLoggingSetup(unittest.TestCase):
    def test_create_logger(self):
        logger = create_logger(__name__)
        self.assertIsNotNone(logger)


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


class TestRegistryFactory(unittest.TestCase):
    def test_create_registry(self):
        in_memory_registry_type = RegistryType.in_memory
        registry = RegistryFactory.create_registry(in_memory_registry_type)
        self.assertIsInstance(registry, InMemoryTaskRegistry)


class TestDiscovery(unittest.TestCase):
    def test_get_discovered_task_by_name(self):
        expected_discovered_task_name = "long_running_task_one"
        func = get_discovered_task_by_name(expected_discovered_task_name)
        actual_discovered_task_name = func.get_task_object().__name__
        self.assertEqual(expected_discovered_task_name, actual_discovered_task_name)

    def test_discover_tasks(self):
        number_of_tasks = discover_tasks()
        self.assertEqual(2, number_of_tasks)


class TestUtils(unittest.TestCase):
    def test_get_worker_port_and_host(self):
        port, host = get_worker_port_and_host()

        self.assertEqual(port, 5690)
        self.assertEqual(host, "localhost")


class TestInMemoryRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = InMemoryTaskRegistry()

        @app.Task
        def hello():
            print("Hello World")

        self.registry.register(hello)

    def test_register_task(self):
        @app.Task
        def scream():
            print("HAAAAYY!!!")

        self.registry.register(scream)
        self.assertEqual(2, len(self.registry))
        self.assertEqual(scream, self.registry["scream"])

    def test_unregister_task(self):
        self.registry.unregister("hello")
        self.assertEqual(0, len(self.registry))
        with self.assertRaises(KeyError):
            self.registry["hello"]


class TaskRunnerForTesting(BaseTaskRunner):
    def execute(self, task_name, **kwargs):
        print(f"Received task name: {task_name} with kwargs", kwargs)


class TestTask(unittest.TestCase):
    def setUp(self):
        @app.Task
        def hello(name):
            print(f"Hello World, {name}")
            return name

        self.func = hello

        self.custom_runner = TaskRunnerForTesting()

        self.worker = WorkerInitializer(number_of_slaves=1)
        self.worker.register_task(hello)

    def test_callable_for_task(self):
        expected_name = "KayPee"
        actual_name = self.func(name=expected_name)
        self.assertEqual(expected_name, actual_name)

    def test_get_task_object(self):
        expected_func_name = "hello"
        actual_func_name = self.func.get_task_object().__name__
        self.assertEqual(expected_func_name, actual_func_name)

    @unittest.skip("Requires to be terminated manually")
    def test_run_task(self):
        old_stdout = sys.stdout
        new_stdout = io.StringIO()
        sys.stdout = new_stdout

        try:
            _ = self.func.run(name="King Pee")
        except KeyboardInterrupt:
            pass
        try:
            self.worker.start()
        except KeyboardInterrupt:
            pass
        output = new_stdout.getvalue()

        self.assertTrue("Hello World, King Pee" in output)
        sys.stdout = old_stdout

    @unittest.skip("Requires to be terminated manually")
    def test_run_task_with_custom_runner(self):
        old_stdout = sys.stdout
        new_stdout = io.StringIO()
        sys.stdout = new_stdout

        try:
            _ = self.func.run(name="King Pee")
        except KeyboardInterrupt:
            pass
        try:
            self.worker.runner = self.custom_runner
            self.worker.start()
        except KeyboardInterrupt:
            pass
        output = new_stdout.getvalue()

        expected = "Received task name: hello with kwargs"
        self.assertTrue(expected in output)
        sys.stdout = old_stdout


if __name__ == "__main__":
    unittest.main()
