"""
Dockerfile parser for Heroku Compatibility Buildpack.
Parses Dockerfile instructions and validates compatibility with Heroku build environment.
"""

import os
import re
import shlex
from typing import Dict, List, Optional, Tuple, Any


class DockerfileParseError(Exception):
    """Custom exception raised when Dockerfile parsing fails or contains unsupported directives."""
    pass


class DockerfileConfig:
    def __init__(self):
        self.base_image: Optional[str] = None
        self.python_version: Optional[str] = None
        self.args: Dict[str, str] = {}
        self.envs: Dict[str, str] = {}
        self.workdir: str = "/app"
        self.run_commands: List[str] = []
        self.apt_packages: List[str] = []
        self.pip_requirements_files: List[str] = []
        self.pip_inline_installs: List[str] = []
        self.chmod_commands: List[str] = []
        self.copy_ops: List[Tuple[str, str]] = []
        self.add_ops: List[Tuple[str, str]] = []
        self.exposed_ports: List[str] = []
        self.cmd: Optional[List[str]] = None
        self.cmd_raw: Optional[str] = None
        self.entrypoint: Optional[List[str]] = None
        self.entrypoint_raw: Optional[str] = None
        self.warnings: List[str] = []


def parse_exec_or_shell_form(value: str) -> Tuple[List[str], str]:
    """
    Parses an exec form (JSON array) or shell form string.
    Returns (args_list, raw_string).
    """
    value_str = value.strip()
    if value_str.startswith("[") and value_str.endswith("]"):
        try:
            import json
            parsed = json.loads(value_str)
            if isinstance(parsed, list):
                return [str(x) for x in parsed], value_str
        except Exception:
            pass
    tokens = shlex.split(value_str)
    return tokens, value_str


def expand_variables(text: str, env_dict: Dict[str, str], arg_dict: Dict[str, str]) -> str:
    """
    Expands $VAR or ${VAR} using ARG and ENV values.
    """
    combined = {}
    combined.update(arg_dict)
    combined.update(env_dict)

    def replace_var(match):
        var_name = match.group(1) or match.group(2)
        return combined.get(var_name, match.group(0))

    pattern = re.compile(r'\$\{([A-Za-z0-9_]+)\}|\$([A-Za-z0-9_]+)')
    return pattern.sub(replace_var, text)


def parse_dockerfile(file_path: str, build_args: Optional[Dict[str, str]] = None) -> DockerfileConfig:
    if not os.path.exists(file_path):
        raise DockerfileParseError(f"Dockerfile not found at {file_path}")

    config = DockerfileConfig()
    if build_args:
        config.args.update(build_args)

    with open(file_path, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    lines = []
    current_line = ""
    for line in raw_lines:
        if line.rstrip().endswith("\\"):
            current_line += line.rstrip()[:-1] + " "
        else:
            current_line += line
            lines.append(current_line)
            current_line = ""
    if current_line:
        lines.append(current_line)

    for line_num, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(None, 1)
        instruction = parts[0].upper()
        args_str = parts[1] if len(parts) > 1 else ""

        expanded_args = expand_variables(args_str, config.envs, config.args)

        if instruction == "ARG":
            if "=" in expanded_args:
                k, v = expanded_args.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k not in config.args:
                    config.args[k] = v
            else:
                k = expanded_args.strip()
                if k and k not in config.args:
                    config.args[k] = ""

        elif instruction == "FROM":
            from_parts = expanded_args.split()
            base_image = from_parts[0]
            config.base_image = base_image

            python_match = re.match(r'^python:(3\.\d+)(?:\.\d+)?(-.*)?$', base_image, re.IGNORECASE)
            if python_match:
                config.python_version = python_match.group(1)
            else:
                raise DockerfileParseError(
                    f"ERROR: Dockerfile detected but unsupported base image: FROM {base_image}\n"
                    f"This buildpack currently supports Python Dockerfiles only."
                )

        elif instruction == "ENV":
            if "=" in expanded_args:
                try:
                    pairs = shlex.split(expanded_args)
                    for pair in pairs:
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            config.envs[k] = v
                        else:
                            config.envs[pair] = ""
                except Exception:
                    k, v = expanded_args.split("=", 1)
                    config.envs[k.strip()] = v.strip()
            else:
                env_parts = expanded_args.split(None, 1)
                if len(env_parts) == 2:
                    config.envs[env_parts[0]] = env_parts[1].strip('"').strip("'")
                elif len(env_parts) == 1:
                    config.envs[env_parts[0]] = ""

        elif instruction == "WORKDIR":
            config.workdir = expanded_args.strip()

        elif instruction == "RUN":
            run_cmd = expanded_args.strip()
            config.run_commands.append(run_cmd)

            if "docker " in run_cmd or run_cmd.startswith("docker"):
                raise DockerfileParseError(f"ERROR: Unsupported Dockerfile instruction: RUN {run_cmd}")

            if "apt-get install" in run_cmd:
                apt_matches = re.findall(r'apt-get\s+install\s+([^\&\;\|]+)', run_cmd)
                for apt_str in apt_matches:
                    tokens = shlex.split(apt_str)
                    for tok in tokens:
                        if tok.startswith("-"):
                            continue
                        if tok and tok not in config.apt_packages:
                            config.apt_packages.append(tok)

            if "pip install" in run_cmd:
                if "-r " in run_cmd:
                    req_matches = re.findall(r'-r\s+([^\s\&\;\|]+)', run_cmd)
                    for req_file in req_matches:
                        if req_file not in config.pip_requirements_files:
                            config.pip_requirements_files.append(req_file)
                else:
                    config.pip_inline_installs.append(run_cmd)

            if "chmod" in run_cmd:
                config.chmod_commands.append(run_cmd)

        elif instruction in ("COPY", "ADD"):
            clean_args = expanded_args
            if "--from=" in clean_args:
                raise DockerfileParseError(f"ERROR: Multi-stage build 'COPY --from' is currently unsupported: {line}")

            clean_args = re.sub(r'--[a-zA-Z0-9_-]+(=[^\s]+)?', '', clean_args).strip()
            tokens, _ = parse_exec_or_shell_form(clean_args)
            if len(tokens) >= 2:
                srcs, dst = tokens[:-1], tokens[-1]
                for src in srcs:
                    if src.startswith("/") or src.startswith(".."):
                        raise DockerfileParseError(
                            f"ERROR: Unsupported Dockerfile instruction: {instruction} from outside context '{src}'"
                        )
                    if instruction == "COPY":
                        config.copy_ops.append((src, dst))
                    else:
                        config.add_ops.append((src, dst))

        elif instruction == "EXPOSE":
            ports = expanded_args.split()
            for p in ports:
                config.exposed_ports.append(p)

        elif instruction == "CMD":
            cmd_list, raw = parse_exec_or_shell_form(expanded_args)
            config.cmd = cmd_list
            config.cmd_raw = raw

        elif instruction == "ENTRYPOINT":
            ep_list, raw = parse_exec_or_shell_form(expanded_args)
            config.entrypoint = ep_list
            config.entrypoint_raw = raw

        elif instruction in ("USER", "SHELL", "LABEL", "MAINTAINER"):
            config.warnings.append(f"Instruction '{instruction}' is noted with Heroku runtime limitations: {expanded_args}")

        elif instruction in ("VOLUME", "HEALTHCHECK", "ONBUILD", "STOPSIGNAL"):
            config.warnings.append(f"Instruction '{instruction}' is not applicable in Heroku slug runtime: {expanded_args}")

        else:
            raise DockerfileParseError(f"ERROR: Unsupported Dockerfile instruction: {line}")

    if not config.base_image:
        raise DockerfileParseError("ERROR: Dockerfile missing 'FROM' instruction.")

    return config
