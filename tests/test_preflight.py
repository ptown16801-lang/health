import importlib.util
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "preflight.py"
SPEC = importlib.util.spec_from_file_location("preflight", MODULE_PATH)
PREFLIGHT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(PREFLIGHT)


class PreflightTests(unittest.TestCase):
    def test_missing_required_package_fails_without_reading_fixture_data(self):
        with (
            mock.patch.object(PREFLIGHT.importlib.metadata, "version", side_effect=PREFLIGHT.importlib.metadata.PackageNotFoundError),
            mock.patch.object(PREFLIGHT.shutil, "which", return_value=None),
        ):
            self.assertEqual(PREFLIGHT.main(), 1)

    def test_optional_tool_is_not_required(self):
        package_versions = {
            package["name"]: package["version"]
            for package in PREFLIGHT.json.loads(
                (PREFLIGHT.ROOT / "config/dependencies.json").read_text()
            )["packages"]
        }

        def which(command):
            return "/local/onenote-tool" if command == "onenote-tool" else None

        completed = PREFLIGHT.subprocess.CompletedProcess([], 0, "usage", "")
        with (
            mock.patch.object(PREFLIGHT.importlib.metadata, "version", side_effect=package_versions.__getitem__),
            mock.patch.object(PREFLIGHT.shutil, "which", side_effect=which),
            mock.patch.object(PREFLIGHT.subprocess, "run", return_value=completed),
        ):
            self.assertEqual(PREFLIGHT.main(), 0)


if __name__ == "__main__":
    unittest.main()
