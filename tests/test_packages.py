import os
import shutil
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lib.packages import install_apt_packages


class TestPackages(unittest.TestCase):

    def setUp(self):
        self.build_dir = tempfile.mkdtemp()
        self.cache_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.build_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    def test_install_apt_packages(self):
        pkgs = ["ffmpeg", "git"]
        installed = install_apt_packages(pkgs, self.build_dir, self.cache_dir)

        # Check .profile.d script creation
        profile_script = os.path.join(self.build_dir, ".profile.d", "001_apt_packages.sh")
        self.assertTrue(os.path.exists(profile_script))

        with open(profile_script, "r") as f:
            content = f.read()
            self.assertIn("HOME/.apt/usr/bin", content)
            self.assertIn("LD_LIBRARY_PATH", content)


if __name__ == "__main__":
    unittest.main()
