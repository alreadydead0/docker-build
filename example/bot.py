import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    logging.info("Starting Example Telegram Bot...")
    bot_token = os.environ.get("BOT_TOKEN")
    api_id = os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")

    if not (bot_token and api_id and api_hash):
        logging.warning("BOT_TOKEN, API_ID, or API_HASH environment variables are not set.")
        logging.info("Set Heroku Config Vars: BOT_TOKEN, API_ID, API_HASH to run active Telegram bot.")

    logging.info("Bot process is initialized and ready.")

if __name__ == "__main__":
    main()
