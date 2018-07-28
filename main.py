#!/usr/bin/env python3
"""
Module Docstring
"""

__author__ = "Dan Timofte"
__version__ = "1.0.0"
__license__ = "MIT"

import os
import logging
import glob
import json
import pickle
from telegram.ext import Updater, CommandHandler
from bitfinex import ClientV1 as Client

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

BTFX = Client(
    os.environ.get('BFX_TELEGRAM_KEY'),
    os.environ.get('BFX_TELEGRAM_SECRET')
)

AUTH_PASS = os.environ.get('AUTH_PASS')

USERSDATA = {}

def read_authentications():
    files = glob.glob('data/usersdata.pickle')
    if not files:
        return {}

    with open(files[0], 'rb') as usersdata_file:
        try:
            pickle_object = pickle.load(usersdata_file)
        except (ValueError, TypeError):
            LOGGER.error(f'error on parsing pickle {ValueError} # {TypeError}')
            return {}
        return pickle_object


def save_authentications():
    userdata_file = "data/usersdata.pickle"
    ensure_dir(userdata_file)
    with open(userdata_file, 'wb') as outfile:
        pickle.dump(USERSDATA, outfile)

    human_readable_file = "data/usersdata.json"
    with open(human_readable_file, 'w') as outfile:
        json.dump(USERSDATA, outfile)


def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)




############ CALLBACK FUNCTIONS
def cb_start(bot, update):
    update.message.reply_text('Here be Dragons')

def cb_auth(bot, update, args):
    chat_id = update.message.chat.id
    username = update.message.chat.username
    first_name = update.message.chat.first_name
    last_name = update.message.chat.last_name

    if len(args) < 1:
        bot.send_message(
            chat_id,
            text='<pre>please run /auth password</pre>',
            parse_mode='HTML'
        )
        return

    botpass = args[0]
    if chat_id in USERSDATA:
        user_data = USERSDATA[chat_id]
    else:
        user_data = {"authenticated" : "no", "failed_auth" : 0}

    if botpass == AUTH_PASS:
        message = "<pre>authentication successfull </pre>"
        bot.send_message(chat_id, text=message, parse_mode='HTML')
        user_data["authenticated"] = "yes"
        user_data["telegram_user"] = username
        user_data["telegram_name"] = f"{first_name} {last_name}"
    else:
        message = "<pre>bad password</pre>"
        bot.send_message(chat_id, text=message, parse_mode='HTML')
        user_data["authenticated"] = "no"
        user_data["failed_auth"] += 1
        user_data["telegram_user"] = username
        user_data["telegram_name"] = f"{first_name} {last_name}"
        USERSDATA[chat_id] = user_data
        save_authentications()


def cb_error(bot, update, boterror):
    """Log Errors caused by Updates."""
    LOGGER.warning(f'Update "{update}" caused error "{boterror}"')


def main():
    LOGGER.info("Here be dragons")

    updater = Updater(os.environ.get('TELEGRAM_TOKEN'))
    # Get the dispatcher to register handlers
    qdp = updater.dispatcher

    # on different commands - answer in Telegram
    qdp.add_handler(CommandHandler("start", cb_start))
    qdp.add_handler(CommandHandler("auth", cb_auth,pass_args=True))

    # log all errors
    qdp.add_error_handler(cb_error)

    # Start the Bot
    updater.start_polling(timeout=60, read_latency=0.2)

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()



if __name__ == "__main__":
    main()
