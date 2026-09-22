import os
import shutil
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lib.python_runtime import setup_python_runtime


class TestPythonRuntime(unittest.TestCase):

    def setUp(self):
        self.build_dir = tempfile.mkdtemp()
        self.cache_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.build_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    def test_setup_python_runtime(self):
        python_bin = setup_python_runtime("3.12", self.build_dir, self.cache_dir)
        self.assertTrue(os.path.exists(python_bin))
        self.assertTrue(os.path.exists(os.path.join(self.build_dir, "runtime.txt")))

        # Check .profile.d script
        profile_script = os.path.join(self.build_dir, ".profile.d", "000_python.sh")
        self.assertTrue(os.path.exists(profile_script))
        with open(profile_script, "r") as f:
            content = f.read()
            self.assertIn("PATH=\"$HOME/.heroku/python/bin:$PATH\"", content)


if __name__ == "__main__":
    unittest.main()
