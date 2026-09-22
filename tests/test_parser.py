import os
import tempfile
import unittest
import sys

# Ensure lib directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lib.dockerfile_parser import parse_dockerfile, DockerfileParseError


class TestDockerfileParser(unittest.TestCase):

    def create_temp_dockerfile(self, content: str) -> str:
        tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".Dockerfile")
        tmp.write(content)
        tmp.close()
        return tmp.name

    def test_valid_python_312_slim(self):
        content = """
        FROM python:3.12-slim
        WORKDIR /app
        COPY requirements.txt .
        RUN pip install -r requirements.txt
        COPY . .
        CMD ["python", "bot.py"]
        """
        path = self.create_temp_dockerfile(content)
        try:
            config = parse_dockerfile(path)
            self.assertEqual(config.base_image, "python:3.12-slim")
            self.assertEqual(config.python_version, "3.12")
            self.assertEqual(config.workdir, "/app")
            self.assertIn("requirements.txt", config.pip_requirements_files)
            self.assertEqual(config.cmd, ["python", "bot.py"])
        finally:
            os.remove(path)

    def test_valid_python_311_slim_with_apt(self):
        content = """
        FROM python:3.11-slim
        RUN apt-get update && apt-get install -y ffmpeg aria2 git
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt
        COPY . .
        CMD ["python", "main.py"]
        """
        path = self.create_temp_dockerfile(content)
        try:
            config = parse_dockerfile(path)
            self.assertEqual(config.python_version, "3.11")
            self.assertIn("ffmpeg", config.apt_packages)
            self.assertIn("aria2", config.apt_packages)
            self.assertIn("git", config.apt_packages)
            self.assertEqual(config.cmd, ["python", "main.py"])
        finally:
            os.remove(path)

    def test_unsupported_base_image(self):
        content = """
        FROM node:22
        WORKDIR /app
        """
        path = self.create_temp_dockerfile(content)
        try:
            with self.assertRaises(DockerfileParseError) as ctx:
                parse_dockerfile(path)
            self.assertIn("unsupported base image: FROM node:22", str(ctx.exception))
        finally:
            os.remove(path)

    def test_env_and_arg_handling(self):
        content = """
        ARG PYTHON_VER=3.10
        FROM python:${PYTHON_VER}-slim
        ENV PYTHONUNBUFFERED=1
        ENV TZ="Asia/Kolkata" APP_MODE=prod
        WORKDIR /app
        CMD python bot.py
        """
        path = self.create_temp_dockerfile(content)
        try:
            config = parse_dockerfile(path)
            self.assertEqual(config.python_version, "3.10")
            self.assertEqual(config.envs.get("PYTHONUNBUFFERED"), "1")
            self.assertEqual(config.envs.get("TZ"), "Asia/Kolkata")
            self.assertEqual(config.envs.get("APP_MODE"), "prod")
            self.assertEqual(config.cmd, ["python", "bot.py"])
        finally:
            os.remove(path)

    def test_unsupported_docker_run(self):
        content = """
        FROM python:3.12
        RUN docker build -t myapp .
        """
        path = self.create_temp_dockerfile(content)
        try:
            with self.assertRaises(DockerfileParseError) as ctx:
                parse_dockerfile(path)
            self.assertIn("Unsupported Dockerfile instruction: RUN docker build", str(ctx.exception))
        finally:
            os.remove(path)

    def test_entrypoint_and_cmd(self):
        content = """
        FROM python:3.13
        ENTRYPOINT ["python"]
        CMD ["bot.py"]
        """
        path = self.create_temp_dockerfile(content)
        try:
            config = parse_dockerfile(path)
            self.assertEqual(config.entrypoint, ["python"])
            self.assertEqual(config.cmd, ["bot.py"])
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
