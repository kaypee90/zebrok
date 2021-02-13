import unittest
from zebrok.utils import (
    get_worker_port_and_host,
    resolve_hostname,
    get_socket_address_from_conf,
)
from zebrok.registry import InMemoryTaskRegistry
from zebrok import app
from zebrok.worker import WorkerInitializer
from zebrok.discovery import get_discovered_task_by_name


class TestDiscovery(unittest.TestCase):

    def test_get_discovered_task_by_name(self):
        expected_discovered_task_name = "long_running_task_one"
        func = get_discovered_task_by_name(expected_discovered_task_name)
        actual_discovered_task_name = func.get_task_object().__name__
        self.assertEqual(expected_discovered_task_name, actual_discovered_task_name)


class TestUtils(unittest.TestCase):

    def test_get_worker_port_and_host(self):
        port, host = get_worker_port_and_host()

        self.assertEqual(port, 5690)
        self.assertEqual(host, "localhost")

    def test_resolve_hostname(self):
        host_ip = resolve_hostname("localhost")
        self.assertEqual(host_ip, "127.0.0.1")

    def test_get_socket_address_from_conf(self):
        address = get_socket_address_from_conf()
        self.assertEqual(address, "tcp://127.0.0.1:5690")


class TestRegistry(unittest.TestCase):

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


class TestTask(unittest.TestCase):

    def setUp(self):
        @app.Task
        def hello(name):
            print(f"Hello World, {name}")
            return name

        self.func = hello

        self.worker = WorkerInitializer()
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
        result = self.func.run(name="Kwabena")
        self.worker.start()
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
