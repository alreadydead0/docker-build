import os
import shutil
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lib.dockerfile_parser import DockerfileConfig
from lib.process import determine_process_cmd, determine_process_type, generate_procfile_and_env, parse_heroku_yml


class TestProcess(unittest.TestCase):

    def setUp(self):
        self.build_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.build_dir, ignore_errors=True)

    def test_determine_process_cmd(self):
        config = DockerfileConfig()
        config.cmd = ["python", "bot.py"]
        self.assertEqual(determine_process_cmd(config), "python bot.py")

        config.entrypoint = ["python"]
        config.cmd = ["main.py"]
        self.assertEqual(determine_process_cmd(config), "python main.py")

    def test_determine_process_type(self):
        config = DockerfileConfig()
        self.assertEqual(determine_process_type(config, "python bot.py"), "worker")
        self.assertEqual(determine_process_type(config, "uvicorn app:main"), "web")
        self.assertEqual(determine_process_type(config, "python bot.py", heroku_docker_process="web"), "web")

    def test_heroku_yml_detection(self):
        config = DockerfileConfig()

        # Test heroku.yml with worker
        heroku_yml = os.path.join(self.build_dir, "heroku.yml")
        with open(heroku_yml, "w") as f:
            f.write("build:\n  docker:\n    worker: Dockerfile\nrun:\n  worker: python bot.py\n")

        self.assertEqual(parse_heroku_yml(self.build_dir), "worker")
        self.assertEqual(determine_process_type(config, "python bot.py", build_dir=self.build_dir), "worker")

        # Test heroku.yml with web
        with open(heroku_yml, "w") as f:
            f.write("build:\n  docker:\n    web: Dockerfile\nrun:\n  web: python main.py\n")

        self.assertEqual(parse_heroku_yml(self.build_dir), "web")
        self.assertEqual(determine_process_type(config, "python bot.py", build_dir=self.build_dir), "web")

    def test_generate_procfile_and_env(self):
        config = DockerfileConfig()
        config.cmd = ["python", "bot.py"]
        config.envs["PYTHONUNBUFFERED"] = "1"
        config.envs["SECRET_KEY"] = "mysecret"

        proc_line = generate_procfile_and_env(config, self.build_dir)
        self.assertEqual(proc_line, "worker: python bot.py")

        procfile = os.path.join(self.build_dir, "Procfile")
        self.assertTrue(os.path.exists(procfile))
        with open(procfile, "r") as f:
            self.assertEqual(f.read().strip(), "worker: python bot.py")

        env_script = os.path.join(self.build_dir, ".profile.d", "000_dockerfile_env.sh")
        self.assertTrue(os.path.exists(env_script))
        with open(env_script, "r") as f:
            content = f.read()
            self.assertIn('export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"', content)
            self.assertIn('export SECRET_KEY="${SECRET_KEY:-mysecret}"', content)

    def test_procfile_precedence(self):
        # Create existing Procfile
        procfile = os.path.join(self.build_dir, "Procfile")
        with open(procfile, "w") as f:
            f.write("worker: python custom.py\n")

        config = DockerfileConfig()
        config.cmd = ["python", "bot.py"]

        generate_procfile_and_env(config, self.build_dir)

        # Confirm existing Procfile was not overwritten
        with open(procfile, "r") as f:
            self.assertEqual(f.read().strip(), "worker: python custom.py")


if __name__ == "__main__":
    unittest.main()
