#!/usr/bin/env python3
"""
Module Docstring
"""

__author__ = "Dan Timofte"
__version__ = "1.0.0"
__license__ = "MIT"

import os
import logging

from telegram.ext import Updater, CommandHandler


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


def start(bot, update):
    update.message.reply_text('Here be Dragons')


def error(bot, update, boterror):
    """Log Errors caused by Updates."""
    LOGGER.warning(f'Update "{update}" caused error "{boterror}"')

def main():
    LOGGER.info("Here be dragons")

    updater = Updater(os.environ.get('TELEGRAM_TOKEN'),)
    # Get the dispatcher to register handlers
    qdp = updater.dispatcher

    # on different commands - answer in Telegram
    qdp.add_handler(CommandHandler("start", start))

    # log all errors
    qdp.add_error_handler(error)

    # Start the Bot
    updater.start_polling(timeout=60, read_latency=0.2)

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()



if __name__ == "__main__":
    main()
