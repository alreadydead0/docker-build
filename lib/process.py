"""
Process generation and environment variable handler for Heroku Compatibility Buildpack.
Handles Procfile generation, CMD/ENTRYPOINT translation, heroku.yml detection, process type determination, and ENV export.
"""

import os
import re
import shlex
from typing import Dict, Optional
from lib.dockerfile_parser import DockerfileConfig


def parse_heroku_yml(build_dir: str) -> Optional[str]:
    """
    Detects heroku.yml in build_dir and checks for worker or web processes.
    Returns 'worker' or 'web' if found, otherwise None.
    """
    heroku_yml_path = os.path.join(build_dir, "heroku.yml")
    if not os.path.exists(heroku_yml_path):
        return None

    try:
        with open(heroku_yml_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for worker or web in heroku.yml
        # Look under 'run:' section or general process definitions
        has_worker = bool(re.search(r'^\s*worker\s*:', content, re.MULTILINE))
        has_web = bool(re.search(r'^\s*web\s*:', content, re.MULTILINE))

        if has_worker and not has_web:
            return "worker"
        elif has_web:
            return "web"
        elif has_worker:
            return "worker"
    except Exception:
        pass

    return None


def determine_process_cmd(config: DockerfileConfig) -> str:
    """
    Combines ENTRYPOINT and CMD into a single command string.
    """
    parts = []
    if config.entrypoint:
        parts.extend(config.entrypoint)
    elif config.entrypoint_raw and not config.cmd:
        parts.append(config.entrypoint_raw)

    if config.cmd:
        parts.extend(config.cmd)
    elif config.cmd_raw and not config.entrypoint:
        parts.append(config.cmd_raw)

    if not parts:
        return "python main.py"

    # Join into executable string
    return " ".join(parts)


def determine_process_type(
    config: DockerfileConfig,
    cmd_str: str,
    heroku_docker_process: Optional[str] = None,
    build_dir: Optional[str] = None
) -> str:
    """
    Determines process type ('worker' or 'web').
    """
    if heroku_docker_process:
        return heroku_docker_process.lower()

    # Check heroku.yml if build_dir is provided
    if build_dir:
        heroku_yml_proc = parse_heroku_yml(build_dir)
        if heroku_yml_proc:
            return heroku_yml_proc

    # Web keywords check in command line (e.g. gunicorn, uvicorn, flask run, hypercorn, waitress)
    web_keywords = ["gunicorn", "uvicorn", "flask", "hypercorn", "waitress", "daphne", "starlette", "fastapi"]
    cmd_lower = cmd_str.lower()
    if any(keyword in cmd_lower for keyword in web_keywords):
        return "web"

    if config.exposed_ports:
        return "web"

    # Default process type for python / telegram bots
    return "worker"


def generate_procfile_and_env(
    config: DockerfileConfig,
    build_dir: str,
    env_vars: Optional[Dict[str, str]] = None
) -> str:
    """
    Generates Procfile if not already present, and exports Dockerfile ENV into .profile.d script.
    Returns generated process command line.
    """
    if env_vars is None:
        env_vars = {}

    procfile_path = os.path.join(build_dir, "Procfile")
    cmd_str = determine_process_cmd(config)
    process_override = env_vars.get("HEROKU_DOCKER_PROCESS")
    process_type = determine_process_type(config, cmd_str, process_override, build_dir=build_dir)

    # 1. Check existing Procfile precedence
    if os.path.exists(procfile_path) and not env_vars.get("OVERRIDE_PROCFILE"):
        print("-----> Existing Procfile found; honoring existing Procfile.")
    else:
        # Generate Procfile
        print(f"-----> Generating Procfile: {process_type}: {cmd_str}")
        with open(procfile_path, "w") as f:
            f.write(f"{process_type}: {cmd_str}\n")

    # 2. Generate .profile.d/000_dockerfile_env.sh for runtime ENV defaults
    profile_d_dir = os.path.join(build_dir, ".profile.d")
    os.makedirs(profile_d_dir, exist_ok=True)
    env_script = os.path.join(profile_d_dir, "000_dockerfile_env.sh")

    with open(env_script, "w") as f:
        f.write("#!/usr/bin/env bash\n")
        f.write("# Export Dockerfile ENV defaults without overriding Heroku Config Vars\n")
        for k, v in config.envs.items():
            # Escape value for shell
            safe_v = v.replace('"', '\\"')
            f.write(f'export {k}="${{{k}:-{safe_v}}}"\n')

    os.chmod(env_script, 0o755)

    return f"{process_type}: {cmd_str}"
