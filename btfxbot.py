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
import re
from  datetime import datetime
from math import pi
import pandas as pd
from bokeh.plotting import figure
from bokeh.io import export_png
from bokeh.layouts import column
from telegram.ext import Updater
from telegram.ext import CallbackQueryHandler, CommandHandler
#ConversationHandler , RegexHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import (TelegramError, TimedOut)

from bitfinex import ClientV1 as Client
from bitfinex import ClientV2 as Client2

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


def isnumber(pnumber):
    num_format = re.compile(r"^[\-]?[0-9]*\.?[0-9]*$")
    if re.match(num_format, pnumber):
        return True
    else:
        return False

def get_date(unixtime):
    time_stamp = unixtime / 1000
    formated_date = datetime.utcfromtimestamp(time_stamp).strftime('%Y-%m-%d %H:%M:%S')
    return formated_date

def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def create_graph(candles_data,symbol):
    candles_df = pd.DataFrame(
        candles_data,
        columns=['date', 'open', 'close', 'high', 'low', 'volume']
    )

    candles_df['date'] = candles_df['date'].apply(get_date)
    candles_df['volume'] = candles_df['volume'].astype(int)
    candles_df["date"] = pd.to_datetime(candles_df["date"])

    # Window length for moving average
    window_length = 14
    candles_df['seq'] = candles_df['date']
    close = candles_df['close'][::-1]
    # Get the difference in price from previous step
    delta = close.diff()
    # Make the positive gains (up) and negative gains (down) Series
    up_gains, down_gains = delta.copy(), delta.copy()
    up_gains[up_gains < 0] = 0
    down_gains[down_gains > 0] = 0
    # Calculate the EWMA
    roll_up1 = up_gains.ewm(
        com=window_length,
        min_periods=0,
        adjust=True,
        ignore_na=False
    ).mean()

    roll_down1 = down_gains.abs().ewm(
        com=window_length,
        min_periods=0,
        adjust=True,
        ignore_na=False
    ).mean()

    # Calculate the RSI based on EWMA
    rs1 = roll_up1 / roll_down1
    rsi1 = 100.0 - (100.0 / (1.0 + rs1))
    candles_df['rsi_ewma'] = rsi1
    candles_df = candles_df[::-1][16:]

    inc = candles_df.close > candles_df.open
    dec = candles_df.open > candles_df.close
    candle_width = 30*60*1000 # half an hour in ms

    tools = "pan,wheel_zoom,box_zoom,reset,save"

    candles_graph = figure(x_axis_type="datetime", tools=tools, plot_width=1000, title=symbol.upper())
    candles_graph.xaxis.major_label_orientation = pi/4
    candles_graph.grid.grid_line_alpha = 0.3
    candles_graph.segment(
        candles_df.date,
        candles_df.high,
        candles_df.date,
        candles_df.low,
        color="black"
    )

    candles_graph.vbar(
        candles_df.date[inc],
        candle_width,
        candles_df.open[inc],
        candles_df.close[inc],
        fill_color="#31d8a1",
        line_color="black"
    )
    candles_graph.vbar(
        candles_df.date[dec],
        candle_width,
        candles_df.open[dec],
        candles_df.close[dec],
        fill_color="#F2583E",
        line_color="black"
    )

    rsi_graph = figure(plot_width=1000, plot_height=100, y_range=(0, 100))
    rsi_graph.xaxis.visible = False
    rsi_graph.multi_line(
        xs=[candles_df.seq]*4,
        ys=[
            candles_df.rsi_ewma,
            [20]*candles_df.shape[0],
            [50]*candles_df.shape[0],
            [80]*candles_df.shape[0]
        ],
        line_color=['red', 'black', 'gray', 'black'],
        line_width=1
    )

    export_png(column(candles_graph, rsi_graph), filename="graph.png")

REST_TYPES = {
    "mmarket" : "market",
    "mlimit"  : "limit",
    "mstop"   : "stop",
    "mtrail"  : "trailing-stop",
    "mfok"    : "fill-or-kill",
    "emarket" : "exchange market",
    "elimit"  : "exchange limit",
    "estop"   : "exchange stop",
    "etrail"  : "exchange trailing-stop",
    "efok"    : "exchange fill-or-kill"
}

REPLY_NEW_ORDER, UPDATE_NEW_ORDER = range(2)

class Btfxbot:
    def __init__(self, telegram_token, auth_pass, btfx_key, btfx_secret):
        LOGGER.info("Here be dragons")
        self.userdata = self.read_userdata()
        self.auth_pass = auth_pass
        self.btfx_client = Client(btfx_key, btfx_secret)
        self.btfx_client2 = Client2(btfx_key, btfx_secret)
        self.btfx_symbols = self.btfx_client.symbols()

        updater = Updater(telegram_token)
        # Get the dispatcher to register handlers
        qdp = updater.dispatcher

        # on different commands - answer in Telegram
        qdp.add_handler(CommandHandler("start", self.cb_start))
        qdp.add_handler(CommandHandler("graph", self.cb_graph, pass_args=True))
        qdp.add_handler(CommandHandler("auth", self.cb_auth, pass_args=True))


        # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO

        #conv_handler = ConversationHandler(
        #    entry_points=[CommandHandler("neworder", self.cb_new_order, pass_args=True)],
        #    states={
        #        REPLY_NEW_ORDER: [CallbackQueryHandler(self.new_order_reply, pass_user_data=True)],
        #        UPDATE_NEW_ORDER: [MessageHandler(Filters.text, self.update_new_order,
        #                                          pass_user_data=True)]
        #    },
        #    fallbacks=[CommandHandler('cancel', cancel)]
        #)
        qdp.add_handler(
            CallbackQueryHandler(
                self.cb_btn_cancel_order,
                pattern=r'^cancel_order:[0-9]+$')
            )

        qdp.add_handler(
            CallbackQueryHandler(
                self.cb_btn_orders,
                pattern=r'^orders:\w+$')
            )

        qdp.add_handler(CommandHandler("neworder", self.cb_new_order, pass_args=True))
        qdp.add_handler(CommandHandler("orders", self.cb_orders, pass_args=True))

        # log all errors
        qdp.add_error_handler(self.cb_error)

        # Start the Bot
        updater.start_polling(timeout=60, read_latency=0.2)

        # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
        # SIGABRT. This should be used most of the time, since start_polling() is
        # non-blocking and will stop the bot gracefully.
        updater.idle()

    def read_userdata(self):
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


    def save_userdata(self):
        userdata_file = "data/usersdata.pickle"
        ensure_dir(userdata_file)
        with open(userdata_file, 'wb') as outfile:
            pickle.dump(self.userdata, outfile)

        human_readable_file = "data/usersdata.json"
        with open(human_readable_file, 'w') as outfile:
            json.dump(self.userdata, outfile)


    ############ CALLBACK FUNCTIONS
    def cb_start(self, bot, update):
        update.message.reply_text('Here be Dragons')


    def cb_graph(self, bot, update, args):
        LOGGER.info(f"{update.message.chat.username} : /graph {args}")
        chat_id = update.message.chat.id

        if chat_id not in self.userdata:
            LOGGER.info("chat id not found in list of chats")
            message = "<pre>You'll Clean That Up Before You Leave</pre>"
            bot.send_message(chat_id, text=message, parse_mode='HTML')
            return
        authenticated = self.userdata[chat_id]['authenticated']
        if authenticated == "no":
            LOGGER.info("user id not authenticated")
            message = "<pre>You'll Clean That Up Before You Leave</pre>"
            bot.send_message(chat_id, text=message, parse_mode='HTML')
            return

        symbol = args[0] if args else "iotusd"

        if symbol not in self.btfx_symbols:
            msgtext = f"incorect symbol , available pairs are {self.btfx_symbols}"
            bot.send_message(chat_id, text=msgtext, parse_mode='HTML')
            return

        tradepair = f"t{symbol.upper()}"

        chat_id = update.message.chat.id
        candles_data = self.btfx_client2.candles("1h", tradepair, "hist", limit='120')
        create_graph(candles_data,symbol)
        bot.send_photo(chat_id=chat_id, photo=open('graph.png', 'rb'))

    def cb_auth(self, bot, update, args):
        chat_id = update.message.chat.id
        username = update.message.chat.username
        first_name = update.message.chat.first_name
        last_name = update.message.chat.last_name
        LOGGER.info(f"{chat_id} {username} : /neworder {args}")
        if len(args) < 1:
            bot.send_message(
                chat_id,
                text='<pre>please run /auth password</pre>',
                parse_mode='HTML'
            )
            return

        botpass = args[0]
        if chat_id in self.userdata:
            userinfo = self.userdata[chat_id]
        else:
            userinfo = {"authenticated" : "no", "failed_auth" : 0}

        if botpass == self.auth_pass:
            message = "<pre>authentication successfull </pre>"
            bot.send_message(chat_id, text=message, parse_mode='HTML')
            userinfo["authenticated"] = "yes"
            userinfo["telegram_user"] = username
            userinfo["telegram_name"] = f"{first_name} {last_name}"
        else:
            message = "<pre>bad password</pre>"
            bot.send_message(chat_id, text=message, parse_mode='HTML')
            userinfo["authenticated"] = "no"
            userinfo["failed_auth"] += 1
            userinfo["telegram_user"] = username
            userinfo["telegram_name"] = f"{first_name} {last_name}"

        self.userdata[chat_id] = userinfo
        self.save_userdata()


    def cb_error(self, bot, update, boterror):
        """Log Errors caused by Updates."""
        LOGGER.warning(f'Update "{update}" caused error "{boterror}"')



    #Bitfinex requests
    def cb_new_order(self, bot, update, args):
        LOGGER.info(f"{update.message.chat.username} : /neworder {args}")
        chat_id = update.message.chat.id

        if chat_id not in self.userdata:
            LOGGER.info("chat id not found in list of chats")
            message = "<pre>You'll Clean That Up Before You Leave</pre>"
            bot.send_message(chat_id, text=message, parse_mode='HTML')
            return
        authenticated = self.userdata[chat_id]['authenticated']
        if authenticated == "no":
            LOGGER.info("user id not authenticated")
            message = "<pre>You'll Clean That Up Before You Leave</pre>"
            bot.send_message(chat_id, text=message, parse_mode='HTML')
            return

        ###### Verify order parameters
        if len(args) < 4:
            lines = []
            lines.append("<pre>")
            lines.append("missing parameters\n")
            lines.append("/neworder ±volume price tradepair tradetype\n")
            lines.append("/neworder -100 4.00 iotusd elimit")
            lines.append("</pre>")
            composed_message = ''.join(lines)
            bot.send_message(chat_id, text=composed_message, parse_mode='HTML')
            return

        volume = args[0]
        price = args[1]
        tradepair = args[2]
        tradetype = args[3]

        if  not isnumber(volume):
            msgtext = f"incorect volume , {volume} is not a number"
            bot.send_message(chat_id, text=msgtext)
            return

        if  not isnumber(price):
            msgtext = f"incorect price , {price} is not a number"
            bot.send_message(chat_id, text=msgtext)
            return

        if tradepair not in self.btfx_symbols:
            msgtext = f"incorect tradepair , available pairs are {self.btfx_symbols}"
            bot.send_message(chat_id, text=msgtext, parse_mode='HTML')
            return

        if tradetype not in REST_TYPES:
            msgtext = f"incorect tradetype , available types are : {REST_TYPES}"
            bot.send_message(chat_id, text=msgtext, parse_mode='HTML')
            return

        side = 'buy' if float(volume) > 0 else 'sell'
        volume = abs(float(volume))
        neworder = self.btfx_client.place_order(
            str(volume),
            price,
            side,
            REST_TYPES[tradetype],
            symbol=tradepair
        )
        orderid = neworder['id']
        lines = []

        lines.append(f"Order {orderid} placed succesfully\n")
        composed_message = ''.join(lines)

        buttons = [
            #InlineKeyboardButton('Update Price', callback_data=f"neworder:updprice:{orderid}"),
            #InlineKeyboardButton('Update Volume', callback_data=f"neworder:updvolume:{orderid}"),
            InlineKeyboardButton('Cancel order', callback_data=f"cancel_order:{orderid}")
        ]
        keyboard = InlineKeyboardMarkup([buttons])

        try:
            update.message.reply_text(composed_message, reply_markup=keyboard)
        except(TimedOut, TelegramError) as error:
            LOGGER.info(f"coult not send message keyboard to {chat_id}")
            LOGGER.info(error)

    #Bitfinex requests
    def cb_orders(self, bot, update, args):
        LOGGER.info(f"{update.message.chat.username} : /neworder {args}")
        chat_id = update.message.chat.id

        if chat_id not in self.userdata:
            LOGGER.info("chat id not found in list of chats")
            message = "<pre>You'll Clean That Up Before You Leave</pre>"
            bot.send_message(chat_id, text=message, parse_mode='HTML')
            return 1
        authenticated = self.userdata[chat_id]['authenticated']
        if authenticated == "no":
            LOGGER.info("user id not authenticated")
            message = "<pre>You'll Clean That Up Before You Leave</pre>"
            bot.send_message(chat_id, text=message, parse_mode='HTML')
            return 1

        buttons = [
            InlineKeyboardButton('Margin', callback_data="orders:margin"),
            InlineKeyboardButton('Exchange', callback_data="orders:exchange")
        ]
        keyboard = InlineKeyboardMarkup([buttons])

        try:
            update.message.reply_text("Whice orders do you want to see ?", reply_markup=keyboard)
        except (TimedOut, TelegramError) as error:
            print(f"coult not send message keyboard to {chat_id}")
            print(error)
        return 0


    def cb_btn_orders(self, bot, update):
        query = update.callback_query
        update.callback_query.answer()
        chat_id = update.callback_query.message.chat.id
        LOGGER.info(f"i got {query.data} from {chat_id}")

        orders_type = query.data.split(':')[1]
        LOGGER.info(f"orders_type : {orders_type}")

        active_orders = self.btfx_client.active_orders()
        for order in active_orders:
            order_id = order['id']
            symbol = order['symbol']
            side = order['side']
            original_amount = order['original_amount']
            price = order['price']
            lines = []
            lines.append(f"{order_id}: {symbol} {side} {original_amount}@{price}")
            composed_message = ''.join(lines)
            buttons = [InlineKeyboardButton('cancel', callback_data=f'cancel_order:{order_id}')]
            keyboard = InlineKeyboardMarkup([buttons])
            try:
                bot.send_message(chat_id, text=composed_message, reply_markup=keyboard)
            except (TimedOut, TelegramError) as error:
                print(f"could not send message {composed_message} to {chat_id}")
                print(error)

        return 0



    def cb_btn_cancel_order(self, bot, update):
        query = update.callback_query
        update.callback_query.answer()
        chat_id = update.callback_query.message.chat.id
        LOGGER.info(f"i got {query.data} from {chat_id}")

        order_id = int(query.data.split(':')[1])
        LOGGER.info(f"orderid : {order_id}")

        del_order = self.btfx_client.delete_order(order_id)
        LOGGER.info(f"del_order : {del_order}")

        return
