"""
Simple client server unit test
"""
import logging
import threading
import unittest
import clientserver
from context import lab_logging

lab_logging.setup(stream_level=logging.INFO)


class TestEchoService(unittest.TestCase):
    """The test"""
    _server = clientserver.Server()
    _server_thread = threading.Thread(target=_server.serve)

    @classmethod
    def setUpClass(cls):
        cls._server_thread.start()

    def setUp(self):
        super().setUp()
        self.client = clientserver.Client()

    # TESTS:

    def test_get_existing_entry(self):
        result = self.client.get("Pius")
        self.assertIsNotNone(result)
        self.assertNotEqual(result, "NOT FOUND")
        self.assertIn("0721-222222", result)

    def test_get_nonexistent_entry(self):
        result = self.client.get("Non Existent")
        self.assertEqual(result, "NOT FOUND")

    def test_get_all_entries(self):
        result = self.client.getall()
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        for name in ["Radek", "Pius", "Joel", "Philipp", "Simon"]:
            self.assertIn(name, result)

    def test_get_empty_name(self):
        result = self.client.get("")
        self.assertEqual(result, "NOT FOUND")

    def test_case_sensitivity(self):
        result = self.client.get("pius")  
        self.assertEqual(result, "NOT FOUND")

    def test_get_all_names(self):
        """Jeden Eintrag einzeln abfragen"""
        entries = {
            "Radek":   "0721-111111",
            "Pius":    "0721-222222",
            "Joel":    "0721-333333",
            "Philipp": "0721-444444",
            "Simon":   "0721-555555",
        }
        for name, number in entries.items():
            result = self.client.get(name)
            self.assertEqual(result, number, f"Falsche Nummer für {name}")

    def test_multiple_requests_same_client(self):
        result1 = self.client.get("Pius")
        self.assertNotEqual(result1, "NOT FOUND")

        result2 = self.client.get("Radek")
        self.assertNotEqual(result2, "NOT FOUND")

        result3 = self.client.getall()
        self.assertIsNotNone(result3)
        self.assertGreater(len(result3), 0)

    def test_error_handling(self):
        result = self.client.get("Nobody")
        self.assertEqual(result, "NOT FOUND")

    def tearDown(self):
        self.client.close()

    @classmethod
    def tearDownClass(cls):
        cls._server._serving = False  # pylint: disable=protected-access
        cls._server_thread.join()


if __name__ == '__main__':
    unittest.main()