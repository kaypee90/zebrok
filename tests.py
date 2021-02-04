import unittest
from zebrok.utils import (pickle_task, unpickle_task, get_worker_port_and_host,
                          resolve_hostname, get_socket_address_from_conf)
from zebrok.registry import TaskRegistry
from zebrok import app
from zebrok.worker import Worker


class TestUtils(unittest.TestCase):

    def test_pickle_task(self):
        task = {"func": "sendemail2", "email": "test2@email.com"}
        pickled_task = pickle_task(task)
        self.assertEqual(
            '{"func": "sendemail2", "email": "test2@email.com"}', pickled_task)

    def test_unpickle_task(self):
        pickled_task = '{"func": "sendemail", "email": "test@email.com"}'
        task = unpickle_task(pickled_task)
        self.assertEqual(
            {"func": "sendemail", "email": "test@email.com"}, task)

    def test_get_worker_port_and_host(self):
        port, host = get_worker_port_and_host()
        self.assertEqual(port, 5690)
        self.assertEqual(host, 'localhost')

    def test_resolve_hostname(self):
        host_ip = resolve_hostname('localhost')
        self.assertEqual(host_ip, '127.0.0.1')

    def test_get_socket_address_from_conf_for_client(self):
        address = get_socket_address_from_conf()
        self.assertEqual(address, 'tcp://127.0.0.1:5690')

    def test_get_socket_address_from_conf_for_worker(self):
        address = get_socket_address_from_conf(True)
        self.assertEqual(address, 'tcp://127.0.0.1:5690')


class TestRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = TaskRegistry()

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
        self.func = hello

        self.worker = Worker()
        self.worker.register(hello)

    @unittest.skip("Requires to be terminated manually")
    def test_run_task(self):
        result = self.func.run(name="Kwabena")
        self.worker.start()
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
