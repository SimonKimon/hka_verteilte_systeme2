"""
Simple client server unit test
"""

import ast
import logging
import socket
import threading
import time
import unittest

import clientserver
import const_cs
from context import lab_logging

lab_logging.setup(stream_level=logging.INFO)


def _wait_for_server(host: str, port: int, timeout_s: float = 2.0) -> None:
    deadline = time.time() + timeout_s
    last_exc = None
    while time.time() < deadline:
        try:
            sock = socket.create_connection((host, port), timeout=0.2)
            sock.close()
            return
        except OSError as exc:
            last_exc = exc
            time.sleep(0.05)
    raise RuntimeError("Server did not become ready") from last_exc


class TestClientServerService(unittest.TestCase):
    """Tests for the lab1 client/server implementation."""

    _server = None
    _server_thread = None

    @classmethod
    def setUpClass(cls):
        # Bind server to an ephemeral port to avoid conflicts with already running notebooks.
        const_cs.PORT = 0
        cls._server = clientserver.Server()
        const_cs.PORT = cls._server.sock.getsockname()[1]

        cls._server_thread = threading.Thread(target=cls._server.serve)
        cls._server_thread.start()  # start server loop in a thread (called only once)
        _wait_for_server(const_cs.HOST, const_cs.PORT)

    def setUp(self):
        super().setUp()
        self.client = clientserver.Client()  # create new client for each test

    def test_get_found(self):
        """GET: known name returns number"""
        result = self.client.get("Joel")
        self.assertEqual(result, "0721-333333")

    def test_get_not_found(self):
        """GET: unknown name returns NOT FOUND"""
        result = self.client.get("DoesNotExist")
        self.assertEqual(result, "NOT FOUND")

    def test_getall(self):
        """GETALL: returns all entries (as dict string)"""
        result = self.client.getall()
        phonebook = ast.literal_eval(result)
        self.assertIsInstance(phonebook, dict)
        self.assertIn("Joel", phonebook)
        self.assertEqual(phonebook["Joel"], "0721-333333")

    def tearDown(self):
        self.client.close()  # terminate client after each test

    @classmethod
    def tearDownClass(cls):
        cls._server._serving = False  # break out of server loop. pylint: disable=protected-access
        cls._server_thread.join()  # wait for server thread to terminate


if __name__ == '__main__':
    unittest.main()
