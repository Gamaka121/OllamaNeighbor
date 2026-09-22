"""Регрессии классификации запросов без запуска GUI."""

import unittest

from main import format_current_datetime_response, is_filesystem_request


class RoutingTests(unittest.TestCase):
    def test_detects_paths_and_file_intent(self):
        self.assertTrue(is_filesystem_request(r"что находится в C:\OllamaNeighbor?"))
        self.assertTrue(is_filesystem_request("прочитай main.py"))
        self.assertFalse(is_filesystem_request("напечатай текст и нажми Enter"))

    def test_formats_confirmed_datetime_by_requested_granularity(self):
        source = "Дата: 22.09.2026\nВремя: 12:34:56\nДень недели: Tuesday"
        self.assertEqual(format_current_datetime_response(source, "скажи только время"), "12:34:56")
        self.assertEqual(format_current_datetime_response(source, "какая сегодня дата"), "22.09.2026")
        self.assertEqual(format_current_datetime_response(source, "какой сегодня день недели"), "Tuesday")


if __name__ == "__main__":
    unittest.main()
