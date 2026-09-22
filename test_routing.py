"""Регрессии классификации запросов без запуска GUI."""

import unittest

from main import (
    apply_explicit_path_precedence,
    format_current_datetime_response,
    is_filesystem_request,
    requires_current_datetime,
)


class RoutingTests(unittest.TestCase):
    def test_detects_paths_and_file_intent(self):
        self.assertTrue(is_filesystem_request(r"что находится в C:\OllamaNeighbor?"))
        self.assertTrue(is_filesystem_request("прочитай main.py"))
        self.assertFalse(is_filesystem_request("напечатай текст и нажми Enter"))

    def test_routes_current_datetime_queries_deterministically(self):
        self.assertTrue(requires_current_datetime("сегодня"))
        self.assertTrue(requires_current_datetime("какой сегодня день"))
        self.assertTrue(requires_current_datetime("который сейчас час"))
        self.assertFalse(requires_current_datetime("расскажи о сегодняшнем дне"))

    def test_explicit_path_overrides_llm_argument(self):
        arguments = {"path": r"C:\Documents\OllamaNeighbor"}
        result = apply_explicit_path_precedence(
            "list_files",
            arguments,
            r"покажи содержимое C:\OllamaNeighbor",
        )
        self.assertEqual(result["path"], r"C:\OllamaNeighbor")

    def test_formats_confirmed_datetime_by_requested_granularity(self):
        source = "Дата: 22.09.2026\nВремя: 12:34:56\nДень недели: Tuesday"
        self.assertEqual(format_current_datetime_response(source, "скажи только время"), "12:34:56")
        self.assertEqual(format_current_datetime_response(source, "какая сегодня дата"), "22.09.2026")
        self.assertEqual(format_current_datetime_response(source, "какой сегодня день недели"), "Tuesday")


if __name__ == "__main__":
    unittest.main()
