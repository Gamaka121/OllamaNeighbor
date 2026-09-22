"""Регрессии безопасного файлового слоя без обращения к реальным данным."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import files


class FilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.notes_patch = patch.object(files, "NOTES_DIR", self.root)
        self.roots_patch = patch.object(files, "READ_ROOTS", (files.PROJECT_DIR, self.root))
        self.notes_patch.start()
        self.roots_patch.start()

    def tearDown(self):
        self.roots_patch.stop()
        self.notes_patch.stop()
        self.temporary.cleanup()

    def test_reports_data_directory(self):
        result = files.get_files_directory()
        self.assertTrue(result["success"])
        self.assertEqual(Path(result["data"]["path"]), self.root)

    def test_create_read_and_delete_have_truthful_results(self):
        created = files.create_text_file("sample", "Привет")
        self.assertTrue(created["success"])
        read = files.read_text_file("sample.txt")
        self.assertTrue(read["success"])
        self.assertEqual(read["data"]["content"], "Привет")
        deleted = files.delete_file("sample.txt")
        self.assertTrue(deleted["success"])
        missing = files.open_file("sample.txt")
        self.assertFalse(missing["success"])

    def test_lists_explicit_allowed_path(self):
        (self.root / "inside.txt").write_text("ok", encoding="utf-8")
        result = files.list_files(str(self.root))
        self.assertTrue(result["success"])
        self.assertIn({"name": "inside.txt", "type": "file"}, result["data"]["entries"])

    def test_rejects_traversal_and_unc_paths(self):
        self.assertFalse(files.list_files("..")["success"])
        self.assertFalse(files.get_path_info(r"\\server\share")["success"])
        self.assertFalse(files.get_path_info(r"C/:ollamaneighbor")["success"])

    def test_finds_nested_file_without_following_links(self):
        nested = self.root / "one" / "two"
        nested.mkdir(parents=True)
        (nested / "target.txt").write_text("ok", encoding="utf-8")
        result = files.find_file(str(self.root), "target.txt")
        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]["matches"]), 1)


if __name__ == "__main__":
    unittest.main()
