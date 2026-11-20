"""Тесты разбора Packages-индекса (офлайн, без сети)."""

import unittest

from src.aptrepo import RepoError, parse_packages_index, select_package

INDEX = """\
Package: alpha
Version: 1.0-1
Architecture: amd64
Depends: beta (>= 2.0), gamma | delta

Package: alpha
Version: 0.9-1
Architecture: amd64
Depends: beta

Package: beta
Version: 2.5-1
Architecture: amd64
Depends: epsilon
Description: line one
  continued line two

Package: gamma
Version: 1.0
Architecture: amd64

Package: delta
Version: 1.0
Architecture: i386
"""


class TestAptRepo(unittest.TestCase):
    def setUp(self):
        self.pkgs = parse_packages_index(INDEX)

    def test_parse_count_and_fields(self):
        self.assertEqual(len(self.pkgs), 5)
        alpha = [p for p in self.pkgs if p.name == "alpha"][0]
        self.assertEqual(alpha.version, "1.0-1")
        self.assertEqual(alpha.architecture, "amd64")
        self.assertEqual(len(alpha.depends), 2)
        self.assertEqual(alpha.depends[0][0].name, "beta")
        self.assertEqual(alpha.depends[1][0].name, "gamma")
        self.assertEqual(alpha.depends[1][1].name, "delta")

    def test_select_exact_version(self):
        p = select_package(self.pkgs, "alpha", "0.9-1")
        self.assertEqual(p.version, "0.9-1")
        self.assertEqual(len(p.depends), 1)

    def test_select_latest(self):
        p = select_package(self.pkgs, "alpha", None)
        self.assertEqual(p.version, "1.0-1")

    def test_select_case_insensitive(self):
        p = select_package(self.pkgs, "ALPHA", "1.0-1")
        self.assertEqual(p.name, "alpha")

    def test_missing_package(self):
        with self.assertRaises(RepoError) as ctx:
            select_package(self.pkgs, "omega", None)
        self.assertIn("не найден", str(ctx.exception))

    def test_missing_version(self):
        with self.assertRaises(RepoError) as ctx:
            select_package(self.pkgs, "alpha", "3.0")
        msg = str(ctx.exception)
        self.assertIn("3.0", msg)
        self.assertIn("0.9-1", msg)
        self.assertIn("1.0-1", msg)


if __name__ == "__main__":
    unittest.main()
