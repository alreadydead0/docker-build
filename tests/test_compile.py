import os
import shutil
import tempfile
import unittest
import subprocess
import sys


class TestCompileAndRelease(unittest.TestCase):

    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.build_dir = tempfile.mkdtemp()
        self.cache_dir = tempfile.mkdtemp()
        self.env_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.build_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)
        shutil.rmtree(self.env_dir, ignore_errors=True)

    def test_compile_test_1(self):
        # Test 1: Python 3.12-slim + requirements.txt + CMD ["python", "bot.py"]
        dockerfile_content = """
        FROM python:3.12-slim
        WORKDIR /app
        COPY requirements.txt .
        RUN pip install -r requirements.txt
        COPY . .
        CMD ["python", "bot.py"]
        """
        with open(os.path.join(self.build_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile_content)

        with open(os.path.join(self.build_dir, "requirements.txt"), "w") as f:
            f.write("requests\n")

        compile_bin = os.path.join(self.repo_root, "bin", "compile")
        res = subprocess.run([compile_bin, self.build_dir, self.cache_dir, self.env_dir],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Compile failed: {res.stderr}")
        self.assertIn("Dockerfile Heroku Compatibility Buildpack build complete!", res.stdout)

        # Check Procfile created
        procfile = os.path.join(self.build_dir, "Procfile")
        self.assertTrue(os.path.exists(procfile))
        with open(procfile, "r") as f:
            self.assertEqual(f.read().strip(), "worker: python bot.py")

        # Test bin/release
        release_bin = os.path.join(self.repo_root, "bin", "release")
        res_rel = subprocess.run([release_bin, self.build_dir], capture_output=True, text=True)
        self.assertEqual(res_rel.returncode, 0)
        self.assertIn("worker: python bot.py", res_rel.stdout)

    def test_compile_test_3_unsupported(self):
        # Test 3: Unsupported FROM node:22
        dockerfile_content = """
        FROM node:22
        WORKDIR /app
        """
        with open(os.path.join(self.build_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile_content)

        compile_bin = os.path.join(self.repo_root, "bin", "compile")
        res = subprocess.run([compile_bin, self.build_dir, self.cache_dir, self.env_dir],
                             capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("unsupported base image: FROM node:22", res.stderr)


if __name__ == "__main__":
    unittest.main()
