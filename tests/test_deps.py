"""Тесты разбора полей Depends."""

import unittest

from src.deps import Dependency, parse_depends, format_depends


class TestParseDepends(unittest.TestCase):
    def test_simple(self):
        r = parse_depends("libc6 (>= 2.34), libfoo")
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0][0].name, "libc6")
        self.assertEqual(r[0][0].operator, ">=")
        self.assertEqual(r[0][0].version, "2.34")
        self.assertEqual(r[1][0].name, "libfoo")

    def test_alternatives(self):
        r = parse_depends("liba | libb, libc")
        self.assertEqual([d.name for d in r[0]], ["liba", "libb"])
        self.assertEqual([d.name for d in r[1]], ["libc"])

    def test_real_curl_depends(self):
        value = (
            "libc6 (>= 2.34), libgssapi-krb5-2 (>= 1.12.1), "
            "libk5crypto3 (>= 1.11), libkeyutils1, libnghttp2-14 (>= 1.30.0), "
            "libpsl5 (>= 0.16.0), librtmp1, libssh2-1 (>= 1.8.0), "
            "libssl3t64 (>= 3.0.0)"
        )
        r = parse_depends(value)
        self.assertEqual(len(r), 9)
        self.assertTrue(r[0][0].satisfied_by("2.39"))
        self.assertFalse(r[0][0].satisfied_by("2.30"))

    def test_operators(self):
        d = Dependency("x", ">=", "1.0")
        self.assertTrue(d.satisfied_by("1.0"))
        self.assertTrue(d.satisfied_by("1.1"))
        self.assertFalse(d.satisfied_by("0.9"))
        d = Dependency("x", "=", "1.0")
        self.assertTrue(d.satisfied_by("1.0"))
        self.assertFalse(d.satisfied_by("1.0-1"))
        d = Dependency("x", ">>", "1.0")
        self.assertFalse(d.satisfied_by("1:0.9"))
        self.assertTrue(d.satisfied_by("0:1.1"))
        self.assertFalse(d.satisfied_by("2:1.0"))
        d = Dependency("x", "<<", "2.0")
        self.assertFalse(d.satisfied_by("1:3.0"))
        self.assertTrue(d.satisfied_by("1:1.9"))
        d = Dependency("x", "!=", "1.0")
        self.assertTrue(d.satisfied_by("1.1"))

    def test_empty(self):
        self.assertEqual(parse_depends(""), [])
        self.assertEqual(parse_depends("  "), [])

    def test_roundtrip(self):
        v = "libc6 (>= 2.34), a | b"
        self.assertEqual(
            format_depends(parse_depends(v)), "libc6 (>= 2.34), a | b"
        )

    def test_bad_atom(self):
        with self.assertRaises(ValueError):
            parse_depends("lib 123")


if __name__ == "__main__":
    unittest.main()
