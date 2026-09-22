FROM python:3.12-slim

# Install system dependencies (ffmpeg, aria2, git)
RUN apt-get update && apt-get install -y ffmpeg aria2 git

WORKDIR /app

# Copy dependency manifest and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Set default process execution
CMD ["python", "bot.py"]
