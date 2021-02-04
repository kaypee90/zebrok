import unittest
from zebrok.utils import (pickle_task, unpickle_task, get_worker_port_and_host,
    resolve_hostname, get_socket_address_from_conf)

class TestUtils(unittest.TestCase):

    def test_pickle_task(self):
        task = {"func":"sendemail2", "email":"test2@email.com"}
        pickled_task = pickle_task(task)
        self.assertEqual('{"func": "sendemail2", "email": "test2@email.com"}', pickled_task)

    def test_unpickle_task(self):
        pickled_task = '{"func": "sendemail", "email": "test@email.com"}'    
        task = unpickle_task(pickled_task)
        self.assertEqual({"func":"sendemail", "email":"test@email.com"}, task)

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
    

if __name__ == '__main__':
    unittest.main()