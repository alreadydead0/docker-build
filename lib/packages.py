"""
APT system package management for Heroku Compatibility Buildpack.
Downloads, extracts, and configures Debian packages into build_dir/.apt.
"""

import os
import shutil
import subprocess
import sys
from typing import List


def install_apt_packages(packages: List[str], build_dir: str, cache_dir: str) -> List[str]:
    """
    Installs requested APT packages into build_dir/.apt directory.
    Configures .profile.d script for runtime binary and library paths.
    """
    if not packages:
        return []

    apt_dir = os.path.join(build_dir, ".apt")
    os.makedirs(apt_dir, exist_ok=True)
    apt_cache = os.path.join(cache_dir, "apt", "archives")
    os.makedirs(apt_cache, exist_ok=True)

    installed_packages = []

    # Filter duplicate packages
    packages = list(dict.fromkeys(packages))

    print(f"-----> Installing APT system packages: {', '.join(packages)}")

    # Check if apt-get is available
    has_apt = shutil.which("apt-get") is not None and shutil.which("dpkg-deb") is not None

    if has_apt:
        try:
            # Update apt cache if possible
            subprocess.run(["apt-get", "update", "-qq"], check=False, stderr=subprocess.DEVNULL)

            # Download deb packages into cache
            cmd = ["apt-get", "download", "-qq"] + packages
            subprocess.run(cmd, cwd=apt_cache, check=False, stderr=subprocess.DEVNULL)

            # Unpack all downloaded .deb files into build_dir/.apt
            for f in os.listdir(apt_cache):
                if f.endswith(".deb"):
                    deb_path = os.path.join(apt_cache, f)
                    subprocess.run(["dpkg-deb", "-x", deb_path, apt_dir], check=False, stderr=subprocess.DEVNULL)
                    installed_packages.append(f)
        except Exception as e:
            print(f"       Notice: apt download failed ({e}), checking system binaries.")

    # Fallback: Check system binaries for common tools like ffmpeg, aria2, git, gcc, make
    bin_dir = os.path.join(apt_dir, "usr", "bin")
    os.makedirs(bin_dir, exist_ok=True)

    for pkg in packages:
        pkg_bin = shutil.which(pkg)
        if pkg_bin and not os.path.exists(os.path.join(bin_dir, pkg)):
            try:
                shutil.copy2(pkg_bin, os.path.join(bin_dir, pkg))
                installed_packages.append(pkg)
            except Exception:
                pass

    # Create .profile.d script for system package runtime paths
    profile_d_dir = os.path.join(build_dir, ".profile.d")
    os.makedirs(profile_d_dir, exist_ok=True)
    profile_script = os.path.join(profile_d_dir, "001_apt_packages.sh")

    with open(profile_script, "w") as f:
        f.write("#!/usr/bin/env bash\n")
        f.write("export PATH=\"$HOME/.apt/usr/bin:$HOME/.apt/bin:$PATH\"\n")
        f.write("export LD_LIBRARY_PATH=\"$HOME/.apt/usr/lib/x86_64-linux-gnu:$HOME/.apt/usr/lib:$HOME/.apt/lib/x86_64-linux-gnu:$HOME/.apt/lib:$LD_LIBRARY_PATH\"\n")
        f.write("export LIBRARY_PATH=\"$HOME/.apt/usr/lib/x86_64-linux-gnu:$HOME/.apt/usr/lib:$HOME/.apt/lib/x86_64-linux-gnu:$HOME/.apt/lib:$LIBRARY_PATH\"\n")
        f.write("export CPATH=\"$HOME/.apt/usr/include:$HOME/.apt/usr/include/x86_64-linux-gnu:$CPATH\"\n")
        f.write("export PKG_CONFIG_PATH=\"$HOME/.apt/usr/lib/x86_64-linux-gnu/pkgconfig:$HOME/.apt/usr/lib/pkgconfig:$HOME/.apt/lib/pkgconfig:$PKG_CONFIG_PATH\"\n")

    os.chmod(profile_script, 0o755)

    return installed_packages
