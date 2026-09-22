# Universal Dockerfile-Compatible Heroku Buildpack

A production-ready custom Heroku Buildpack that allows Python repositories containing a `Dockerfile` to be deployed through the official **Heroku Dashboard → Deploy → GitHub → Deploy Branch** workflow.

## Overview & Architecture

When Heroku's normal GitHub deployment detects this buildpack, the buildpack parses the repository's `Dockerfile` and reproduces its build and runtime behavior inside a standard Heroku slug.

> **Important Limitation Notice:**
> This buildpack **does NOT** run `docker build` or require a Docker daemon inside Heroku. It translates supported Dockerfile directives (`FROM`, `RUN`, `ENV`, `WORKDIR`, `COPY`, `ADD`, `EXPOSE`, `CMD`, `ENTRYPOINT`) into equivalent Heroku build operations resulting in a standard Heroku slug compatible with the Heroku-24 / Heroku-26 runtime.

```
Dockerfile ──► Custom Buildpack ──► Heroku Slug ──► Standard Heroku Dyno
```

---

## Dockerfile Feature Support Matrix

| Dockerfile Instruction | Support Level | Heroku Slug Translation Behavior |
| :--- | :--- | :--- |
| `FROM` | Supported | Supports `python:3.10`, `3.11`, `3.12`, `3.13` (and `-slim` variants). Configures `.heroku/python` runtime. Unsupported base images (e.g. `node:22`) fail gracefully with clear errors. |
| `RUN` | Safe Translation | Recognizes `apt-get install -y <pkg>` (`ffmpeg`, `aria2`, `git`, `gcc`, `g++`, `make`, `libffi-dev`, `libssl-dev`) and vendors binaries into `.apt/`. Translates `pip install` and `chmod`. Arbitrary docker commands like `docker build` are rejected. |
| `COPY` / `ADD` | Supported | Application files are already supplied by Heroku build context. Maps destination paths cleanly without duplicating files. Rejects relative path escapes (`../`). |
| `WORKDIR` | Supported | Translates `/app` into standard Heroku application working directory semantics (`/app` / `$HOME`). |
| `ENV` | Supported | Generates `.profile.d/000_dockerfile_env.sh` exporting default environment variables without overriding Heroku Config Vars (`export KEY="${KEY:-default}"`). |
| `ARG` | Supported | Expanded during build context variable substitution. |
| `EXPOSE` | Detection Only | Inspects exposed ports. Does not force `web` process unless HTTP application server is explicitly detected or requested. |
| `CMD` | Supported | Translates exec form `["python", "bot.py"]` or shell form `python bot.py` into Procfile definition. |
| `ENTRYPOINT` | Supported | Combined with `CMD` into unified start command (`ENTRYPOINT` + `CMD`). |
| `USER` | Documented Limitation | Heroku dynos run as unprivileged non-root users (`dyno`). `USER` directives are noted but non-root execution is enforced by Heroku dyno isolation. |
| `SHELL` | Documented Limitation | Heroku buildpack compilation executes commands via standard Bash shell environment. |
| `VOLUME` | Unsupported | Ephemeral filesystem notice: Heroku dynos use ephemeral filesystems. Persistent storage should use S3 / Cloud storage. |
| `HEALTHCHECK` | Unsupported | Health checks are managed by Heroku routing and process manager. |
| `ONBUILD` | Unsupported | Multi-stage build triggers are not applicable to Heroku slug builds. |
| `STOPSIGNAL` | Unsupported | Process termination signal handling is managed by Heroku dyno lifecycle (`SIGTERM`). |

---

## Installation & GitHub Deployment Guide

1. **Add Buildpack to Heroku App**:
   - Open your Heroku Dashboard and select your App.
   - Go to **Settings** → **Buildpacks** → **Add buildpack**.
   - Enter the Git URL of this repository and click **Save changes**.

2. **Connect GitHub Repository**:
   - Go to **Deploy** tab in Heroku Dashboard.
   - Under **Deployment method**, select **GitHub**.
   - Search and select your GitHub repository containing a `Dockerfile`.

3. **Deploy Branch**:
   - Choose your branch (e.g., `main` or `master`) and click **Deploy Branch**.
   - Heroku will automatically detect the buildpack, parse your `Dockerfile`, build dependencies, and launch your application dyno.

---

## Existing Heroku Files & Precedence Rules

If your repository contains existing Heroku files (`heroku.yml`, `Procfile`), the following precedence hierarchy applies:

```
Explicit Heroku Config Vars / HEROKU_DOCKER_PROCESS
              ↓
Existing Procfile
              ↓
Existing heroku.yml (detects worker vs web)
              ↓
Dockerfile CMD / ENTRYPOINT Instructions
              ↓
Buildpack Default (worker: python main.py)
```

---

## Heroku-24 & Heroku-26 Compatibility

This buildpack builds standard Heroku slugs natively compatible with `heroku-24` (Ubuntu 24.04 LTS Noble Numbat) and `heroku-26` stacks. All binaries vendored into `.apt/` and `.heroku/python` target standard 64-bit Linux environments (`x86_64-linux-gnu`).

---

## Security Policy

- **No Arbitrary Execution**: Dockerfile instructions are validated against safety filters before execution. Commands like `RUN docker build` or systemctl modifications fail gracefully with explicit errors.
- **Secret Protection**: Secret variables (`BOT_TOKEN`, `API_HASH`, `DATABASE_URL`, etc.) defined in Heroku Config Vars or Dockerfile `ENV` are never printed to build output logs.
