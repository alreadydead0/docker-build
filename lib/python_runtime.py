"""
Python runtime setup and management for Heroku Compatibility Buildpack.
Configures Python runtime environment in build directory and profile scripts.
"""

import os
import shutil
import subprocess
import sys


DEFAULT_PYTHON_VERSIONS = {
    "3.10": "python-3.10.13",
    "3.11": "python-3.11.8",
    "3.12": "python-3.12.2",
    "3.13": "python-3.13.0",
}


def setup_python_runtime(python_version: str, build_dir: str, cache_dir: str) -> str:
    """
    Ensures Python runtime is configured in build_dir/.heroku/python.
    Returns path to python executable in build directory.
    """
    heroku_dir = os.path.join(build_dir, ".heroku")
    python_dir = os.path.join(heroku_dir, "python")
    os.makedirs(python_dir, exist_ok=True)

    # Generate runtime.txt if not present
    runtime_txt_path = os.path.join(build_dir, "runtime.txt")
    if not os.path.exists(runtime_txt_path):
        full_version = DEFAULT_PYTHON_VERSIONS.get(python_version, f"python-{python_version}")
        with open(runtime_txt_path, "w") as f:
            f.write(f"{full_version}\n")

    # Create virtual environment inside build_dir/.heroku/python if python bin doesn't exist
    venv_python = os.path.join(python_dir, "bin", "python")
    venv_pip = os.path.join(python_dir, "bin", "pip")

    if not os.path.exists(venv_python):
        # Use current system python to create virtualenv in .heroku/python
        subprocess.run([sys.executable, "-m", "venv", python_dir], check=True)

    # Ensure pip is upgraded and available
    subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
                   check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Create .profile.d script for Heroku runtime environment
    profile_d_dir = os.path.join(build_dir, ".profile.d")
    os.makedirs(profile_d_dir, exist_ok=True)
    profile_script = os.path.join(profile_d_dir, "000_python.sh")

    with open(profile_script, "w") as f:
        f.write("#!/usr/bin/env bash\n")
        f.write("export PATH=\"$HOME/.heroku/python/bin:$PATH\"\n")
        f.write("export PYTHONUNBUFFERED=1\n")

    os.chmod(profile_script, 0o755)

    return venv_python
