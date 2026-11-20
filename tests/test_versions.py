"""Тесты сравнения версий Debian (включая векторы из testsuite dpkg)."""

import unittest

from src.versions import Version, compare_versions


def sign(va, vb):
    r = compare_versions(va, vb)
    return (r > 0) - (r < 0)


class TestCompareVersions(unittest.TestCase):
    vectors = [
        ("0.9999", "0.10000", -1),
        ("1:2", "3", 1),
        ("2 alpha:3", "3", -1),
        ("2 alpha:3", "2 alpha:4", -1),
        ("1.1", "1.1.1", -1),
        ("1.0a", "1.0b", -1),
        ("1.0~a", "1.0", -1),
        ("1.0a", "1.0", 1),
        ("1.0~~", "1.0~", -1),
        ("1.0~~~", "1.0~~", -1),
        ("1.0~~~a", "1.0~~a", -1),
        ("1.0", "1.0", 0),
        ("1.10", "1.9", 1),
        ("1.0-1", "1.0", 1),
        ("1.0-1", "1.0-2", -1),
        ("1:1.0", "2.0", 1),
        ("2.0", "1:1.0", -1),
        ("1.0~beta", "1.0", -1),
        ("1.0", "1.0~beta", 1),
        ("1.0~~a", "1.0~a", -1),
        ("1.0a", "1.0a", 0),
        ("1.0.1", "1.0-1", 1),
        ("0.9", "1", -1),
        ("1.0a", "1.01", -1),
        ("1.0a", "1.0a1", -1),
        ("1.0~beta1", "1.0~beta2", -1),
        ("1.0~beta2", "1.0~beta10", -1),
        ("1.0~beta10", "1.0", -1),
        ("8.5.0-2ubuntu10", "8.5.0-2ubuntu10.1", -1),
    ]

    def test_vectors(self):
        for va, vb, expected in self.vectors:
            self.assertEqual(sign(va, vb), expected, f"{va} vs {vb}")
            self.assertEqual(sign(vb, va), -expected, f"{vb} vs {va}")

    def test_parse(self):
        v = Version.parse("1:2.0-1ubuntu2")
        self.assertEqual(v.epoch, 1)
        self.assertEqual(v.upstream, "2.0")
        self.assertEqual(v.revision, "1ubuntu2")
        self.assertEqual(str(v), "1:2.0-1ubuntu2")
        v = Version.parse("14-20240412-0ubuntu1")
        self.assertEqual(v.upstream, "14")
        self.assertEqual(v.revision, "20240412-0ubuntu1")

    def test_parse_invalid(self):
        for bad in ("", "1.0-", "-1", "1-2-", ":1"):
            with self.assertRaises(ValueError, msg=bad):
                Version.parse(bad)


if __name__ == "__main__":
    unittest.main()
