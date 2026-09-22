import os
import shutil
import tempfile
import unittest
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestPromptScenarios(unittest.TestCase):

    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.build_dir = tempfile.mkdtemp()
        self.cache_dir = tempfile.mkdtemp()
        self.env_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.build_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)
        shutil.rmtree(self.env_dir, ignore_errors=True)

    def test_scenario_1_python_312_slim(self):
        """Test 1: Python 3.12-slim + requirements installed + worker process = python bot.py"""
        dockerfile = """
        FROM python:3.12-slim
        WORKDIR /app
        COPY requirements.txt .
        RUN pip install -r requirements.txt
        COPY . .
        CMD ["python", "bot.py"]
        """
        with open(os.path.join(self.build_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile)
        with open(os.path.join(self.build_dir, "requirements.txt"), "w") as f:
            f.write("urllib3\n")

        compile_bin = os.path.join(self.repo_root, "bin", "compile")
        res = subprocess.run([compile_bin, self.build_dir, self.cache_dir, self.env_dir],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Compilation failed: {res.stderr}")

        procfile = os.path.join(self.build_dir, "Procfile")
        self.assertTrue(os.path.exists(procfile))
        with open(procfile, "r") as f:
            self.assertEqual(f.read().strip(), "worker: python bot.py")

        runtime_txt = os.path.join(self.build_dir, "runtime.txt")
        self.assertTrue(os.path.exists(runtime_txt))
        with open(runtime_txt, "r") as f:
            self.assertIn("python-3.12", f.read())

    def test_scenario_2_python_311_slim_ffmpeg(self):
        """Test 2: Python 3.11-slim + ffmpeg dependency + worker process = python main.py"""
        dockerfile = """
        FROM python:3.11-slim
        RUN apt-get update && apt-get install -y ffmpeg
        COPY requirements.txt .
        RUN pip install -r requirements.txt
        COPY . .
        CMD ["python", "main.py"]
        """
        with open(os.path.join(self.build_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile)
        with open(os.path.join(self.build_dir, "requirements.txt"), "w") as f:
            f.write("six\n")

        compile_bin = os.path.join(self.repo_root, "bin", "compile")
        res = subprocess.run([compile_bin, self.build_dir, self.cache_dir, self.env_dir],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Compilation failed: {res.stderr}")

        profile_apt = os.path.join(self.build_dir, ".profile.d", "001_apt_packages.sh")
        self.assertTrue(os.path.exists(profile_apt))

        procfile = os.path.join(self.build_dir, "Procfile")
        with open(procfile, "r") as f:
            self.assertEqual(f.read().strip(), "worker: python main.py")

    def test_scenario_3_unsupported_base_image(self):
        """Test 3: Unsupported FROM node:22"""
        dockerfile = """
        FROM node:22
        WORKDIR /app
        """
        with open(os.path.join(self.build_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile)

        compile_bin = os.path.join(self.repo_root, "bin", "compile")
        res = subprocess.run([compile_bin, self.build_dir, self.cache_dir, self.env_dir],
                             capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("unsupported base image: FROM node:22", res.stderr)

    def test_scenario_4_env_no_secret_leakage(self):
        """Test 4: ENV PYTHONUNBUFFERED=1 and secret handling without secret leakage"""
        dockerfile = """
        FROM python:3.12-slim
        ENV PYTHONUNBUFFERED=1
        ENV BOT_TOKEN=super_secret_bot_token_12345
        CMD ["python", "bot.py"]
        """
        with open(os.path.join(self.build_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile)

        compile_bin = os.path.join(self.repo_root, "bin", "compile")
        res = subprocess.run([compile_bin, self.build_dir, self.cache_dir, self.env_dir],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        # Check secret is NOT printed in build log stdout or stderr
        self.assertNotIn("super_secret_bot_token_12345", res.stdout)
        self.assertNotIn("super_secret_bot_token_12345", res.stderr)

        # Check env script
        env_script = os.path.join(self.build_dir, ".profile.d", "000_dockerfile_env.sh")
        self.assertTrue(os.path.exists(env_script))
        with open(env_script, "r") as f:
            content = f.read()
            self.assertIn('export BOT_TOKEN="${BOT_TOKEN:-super_secret_bot_token_12345}"', content)

    def test_scenario_5_existing_procfile_precedence(self):
        """Test 5: Existing Procfile worker: python custom.py precedence"""
        procfile = os.path.join(self.build_dir, "Procfile")
        with open(procfile, "w") as f:
            f.write("worker: python custom.py\n")

        dockerfile = """
        FROM python:3.12-slim
        CMD ["python", "bot.py"]
        """
        with open(os.path.join(self.build_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile)

        compile_bin = os.path.join(self.repo_root, "bin", "compile")
        res = subprocess.run([compile_bin, self.build_dir, self.cache_dir, self.env_dir],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        with open(procfile, "r") as f:
            self.assertEqual(f.read().strip(), "worker: python custom.py")

    def test_scenario_6_entrypoint_and_cmd_combined(self):
        """Test 6: ENTRYPOINT + CMD combination"""
        dockerfile = """
        FROM python:3.13-slim
        ENTRYPOINT ["python"]
        CMD ["bot.py"]
        """
        with open(os.path.join(self.build_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile)

        compile_bin = os.path.join(self.repo_root, "bin", "compile")
        res = subprocess.run([compile_bin, self.build_dir, self.cache_dir, self.env_dir],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        procfile = os.path.join(self.build_dir, "Procfile")
        with open(procfile, "r") as f:
            self.assertEqual(f.read().strip(), "worker: python bot.py")


if __name__ == "__main__":
    unittest.main()
