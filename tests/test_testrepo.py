"""Тесты парсера тестового репозитория (режим --mode file)."""

import os
import unittest

from src.aptrepo import RepoError
from src.testrepo import load_test_repo, parse_test_repo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ParseTestRepoTests(unittest.TestCase):
    def test_basic_parsing(self):
        pkgs = parse_test_repo(
            "A 1.0: B, C(>=2.0)\n"
            "B 1.0: D|E\n"
            "C 2.0:\n"
            "D 1.0\n"
            "E 3.0-1\n")
        self.assertEqual([p.name for p in pkgs], ["A", "B", "C", "D", "E"])
        self.assertEqual(pkgs[0].version, "1.0")
        self.assertEqual(len(pkgs[0].depends), 2)
        self.assertEqual(pkgs[0].depends[1][0].name, "C")
        self.assertEqual(pkgs[0].depends[1][0].operator, ">=")
        self.assertEqual(len(pkgs[1].depends), 1)
        self.assertEqual(len(pkgs[1].depends[0]), 2)
        self.assertEqual(pkgs[2].depends, [])

    def test_comments_and_blank_lines(self):
        text = "# комментарий\n\nA 1.0: B\n   # вложенный комментарий\nB 1.0\n"
        pkgs = parse_test_repo(text)
        self.assertEqual([p.name for p in pkgs], ["A", "B"])

    def test_uppercase_with_digits(self):
        pkgs = parse_test_repo("BC2 1.0:\n")
        self.assertEqual(pkgs[0].name, "BC2")

    def test_bad_line_reports_path_and_lineno(self):
        with self.assertRaises(RepoError) as cm:
            parse_test_repo("a 1.0: B\n", "r.txt")
        self.assertIn("r.txt:1", str(cm.exception))

    def test_bad_version_reports_lineno(self):
        with self.assertRaises(RepoError) as cm:
            parse_test_repo("A 1.0:\nB .5: C\n", "r.txt")
        msg = str(cm.exception)
        self.assertIn("r.txt:2", msg)

    def test_bad_dependency_reports_lineno(self):
        with self.assertRaises(RepoError) as cm:
            parse_test_repo("A 1.0: B(>=\n", "r.txt")
        self.assertIn("r.txt:1", str(cm.exception))

    def test_load_real_file(self):
        pkgs = load_test_repo(os.path.join(ROOT, "testrepos", "chain.txt"))
        self.assertEqual([p.name for p in pkgs], ["A", "B", "C", "D"])

    def test_load_missing_file(self):
        with self.assertRaises(RepoError):
            load_test_repo(os.path.join(ROOT, "no-such-repo.txt"))


if __name__ == "__main__":
    unittest.main()
