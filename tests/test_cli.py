"""Тесты CLI (этап 1): парсинг, валидация параметров, коды выхода."""

import os
import unittest

from src.cli import ConfigError, parse_args

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAIN = os.path.join(ROOT, "testrepos", "chain.txt")
URL = "http://archive.ubuntu.com/ubuntu/dists/noble/main/binary-amd64/Packages"


class ParseTests(unittest.TestCase):
    def test_defaults(self):
        cfg = parse_args(["-p", "curl", "-s", URL])
        self.assertEqual(cfg.mode, "url")
        self.assertIsNone(cfg.version)
        self.assertEqual(cfg.output, "dependency-graph.png")
        self.assertEqual(cfg.ascii, "off")

    def test_all_six_options(self):
        cfg = parse_args(
            ["-p", "A", "-s", CHAIN, "-m", "file",
             "-v", "2.0-1ubuntu1", "-o", "graph.png", "-a", "tree"])
        self.assertEqual(cfg.package, "A")
        self.assertEqual(cfg.source, CHAIN)
        self.assertEqual(cfg.mode, "file")
        self.assertEqual(cfg.version, "2.0-1ubuntu1")
        self.assertEqual(cfg.output, "graph.png")
        self.assertEqual(cfg.ascii, "tree")

    def test_epoch_version_accepted(self):
        cfg = parse_args(["-p", "curl", "-s", URL, "-v", "1:2.0-1ubuntu2"])
        self.assertEqual(cfg.version, "1:2.0-1ubuntu2")


class ArgErrorTests(unittest.TestCase):
    """Ошибки значений argparse завершаются кодом 2."""

    def _code(self, argv):
        with self.assertRaises(SystemExit) as cm:
            parse_args(argv)
        return cm.exception.code

    def test_missing_required(self):
        self.assertEqual(self._code(["-p", "curl"]), 2)

    def test_bad_package(self):
        self.assertEqual(self._code(["-p", "9x", "-s", URL]), 2)

    def test_bad_version(self):
        self.assertEqual(self._code(["-p", "curl", "-s", URL, "-v", "1."]), 2)

    def test_bad_mode(self):
        self.assertEqual(
            self._code(["-p", "A", "-s", CHAIN, "-m", "ssh"]), 2)

    def test_bad_ascii(self):
        self.assertEqual(
            self._code(["-p", "A", "-s", CHAIN, "-a", "list"]), 2)

    def test_bad_output_extension(self):
        self.assertEqual(
            self._code(["-p", "A", "-s", CHAIN, "-o", "graph.jpg"]), 2)


class ConfigErrorTests(unittest.TestCase):
    """Согласованность параметров — ConfigError (в main() это код выхода 3)."""

    def assert_config_error(self, argv):
        with self.assertRaises(ConfigError):
            parse_args(argv)

    def test_url_mode_non_url_source(self):
        self.assert_config_error(["-p", "curl", "-s", CHAIN, "-m", "url"])

    def test_url_mode_uppercase_package(self):
        self.assert_config_error(["-p", "A", "-s", URL])

    def test_file_mode_url_source(self):
        self.assert_config_error(["-p", "A", "-s", URL, "-m", "file"])

    def test_file_mode_missing_file(self):
        self.assert_config_error(
            ["-p", "A", "-s", os.path.join(ROOT, "nope.txt"), "-m", "file"])

    def test_file_mode_lowercase_package(self):
        self.assert_config_error(["-p", "curl", "-s", CHAIN, "-m", "file"])

    def test_output_dir_missing(self):
        self.assert_config_error(
            ["-p", "A", "-s", CHAIN, "-o", "no/such/dir/g.png"])


class ExitCodeTests(unittest.TestCase):
    """Коды выхода main(): 2 — аргументы, 3 — согласованность."""

    def test_exit_2_missing_args(self):
        from src.__main__ import main

        self.assertEqual(main(["-p", "curl"]), 2)

    def test_exit_3_inconsistent_params(self):
        from src.__main__ import main

        self.assertEqual(main(["-p", "A", "-s", URL, "-m", "file"]), 3)


if __name__ == "__main__":
    unittest.main()
