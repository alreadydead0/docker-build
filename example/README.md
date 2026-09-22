# Example Telegram Bot Repository

This directory contains a sample Python Telegram Bot project ready for deployment on Heroku using the **Dockerfile Heroku Compatibility Buildpack**.

## Structure

- `Dockerfile`: Standard Dockerfile specifying `FROM python:3.12-slim`, system packages (`ffmpeg`, `aria2`, `git`), requirements installation, and `CMD ["python", "bot.py"]`.
- `requirements.txt`: Telegram bot dependencies including `pyrogram`, `TgCrypto`, `aiohttp`, `httpx`, `Pillow`, `ffmpeg-python`, and `beautifulsoup4`.
- `bot.py`: Python entry point script.

## Deploying to Heroku via GitHub Integration

1. Push this repository to GitHub.
2. In the Heroku Dashboard:
   - Go to **Settings** -> **Buildpacks** -> **Add buildpack**.
   - Paste the Git URL of the `dockerfile-heroku-buildpack` repository.
3. Go to **Deploy** -> **Deployment method**: Choose **GitHub**.
4. Connect your GitHub repository and branch.
5. Click **Deploy Branch**.
