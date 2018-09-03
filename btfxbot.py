#!/usr/bin/env python3
"""
Module Docstring
"""

__author__ = "Dan Timofte"
__version__ = "1.0.0"
__license__ = "MIT"


import logging
import threading
from time import sleep
##### telegram libraries
from telegram.ext import Updater
from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import (TelegramError, TimedOut)
##### bitfinex libraries
from bitfinex import ClientV1 as Client
from bitfinex import ClientV2 as Client2
from bitfinex import WssClient

from btfx_gram_utils import bgu_isnumber, bgu_read_userdata, bgu_save_userdata
from btfx_gram_utils import bgu_create_graph

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


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


class Btfxbot:
    def __init__(self, telegram_token, auth_pass, btfx_key, btfx_secret):
        LOGGER.info("Here be dragons")
        self.userdata = bgu_read_userdata()
        self.auth_pass = auth_pass
        self.btfx_client = Client(btfx_key, btfx_secret)
        self.btfx_client2 = Client2(btfx_key, btfx_secret)

        self.btfx_symbols = self.btfx_client.symbols()

        self.btfxwss = WssClient(key=btfx_key, secret=btfx_secret)
        self.btfxwss.authenticate(self.cb_wss_auth)

        self.mywss_thread = threading.Thread(target=self.btfxwss.run, args=())
        self.mywss_thread.daemon = True
        self.mywss_thread.start()
        sleep(2)


        updater = Updater(telegram_token)
        self.tbot = updater.bot
        # Get the dispatcher to register handlers
        qdp = updater.dispatcher

        # on different commands - answer in Telegram
        qdp.add_handler(CommandHandler("start", self.cb_start))
        qdp.add_handler(CommandHandler("graph", self.cb_graph, pass_args=True))
        qdp.add_handler(CommandHandler("auth", self.cb_auth, pass_args=True))
        qdp.add_handler(CommandHandler("option", self.cb_option, pass_args=True))
        qdp.add_handler(CommandHandler("neworder", self.cb_new_order, pass_args=True))
        qdp.add_handler(CommandHandler("orders", self.cb_orders, pass_args=True))

        qdp.add_handler(CallbackQueryHandler(
            self.cb_btn_cancel_order,
            pattern=r'^cancel_order:[0-9]+$'
        ))

        qdp.add_handler(CallbackQueryHandler(
            self.cb_btn_orders,
            pattern=r'^orders:\w+$'
        ))


        # log all errors
        qdp.add_error_handler(self.cb_error)

        # Start the Bot
        updater.start_polling(timeout=60, read_latency=0.2)

        # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
        # SIGABRT. This should be used most of the time, since start_polling() is
        # non-blocking and will stop the bot gracefully.
        updater.idle()


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

        if 'defaultpair' in self.userdata[chat_id]:
            defaultpair = self.userdata[chat_id]['defaultpair']
        else:
            defaultpair = "iotusd"
        symbol = args[0] if args else defaultpair

        if symbol not in self.btfx_symbols:
            msgtext = f"incorect symbol , available pairs are {self.btfx_symbols}"
            bot.send_message(chat_id, text=msgtext, parse_mode='HTML')
            return

        tradepair = f"t{symbol.upper()}"

        chat_id = update.message.chat.id
        candles_data = self.btfx_client2.candles("1h", tradepair, "hist", limit='120')
        active_orders = self.btfx_client.active_orders()
        order_book = self.btfx_client.order_book(
            "iotusd",
            parameters={"limit_bids":800, "limit_asks":800}
        )

        if 'graphtheme' in self.userdata[chat_id]:
            graphtheme = self.userdata[chat_id]['graphtheme']
        else:
            graphtheme = "normal"

        orders_data = order_book['asks'] + order_book['bids']
        bgu_create_graph(candles_data, active_orders, orders_data, symbol, graphtheme=graphtheme)
        bot.send_photo(chat_id=chat_id, photo=open('graph.png', 'rb'))

    def cb_option(self, bot, update, args):
        LOGGER.info(f"{update.message.chat.username} : /option {args}")
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

        if len(args) < 2:
            lines = []
            lines.append("<pre>")
            lines.append("missing parameters\n")
            lines.append("/option defaultpair symbol\n")
            lines.append("  symbols : iotusd, btcusd, ltcusd, ethusd\n")
            lines.append("/option graphtheme theme\n")
            lines.append("  themes : standard, colorblind, monochrome\n")
            lines.append("</pre>")
            composed_message = ''.join(lines)
            bot.send_message(chat_id, text=composed_message, parse_mode='HTML')
            return

        optname = args[0]
        optvalue = args[1]
        if optname not in ['defaultpair', 'graphtheme']:
            lines = []
            lines.append("<pre>")
            lines.append(f"{optname} is not a valid option\n")
            lines.append("valid options are defaultpair and graphtheme\n")
            lines.append("</pre>")
            composed_message = ''.join(lines)
            bot.send_message(chat_id, text=composed_message, parse_mode='HTML')
            return

        if optname == "defaultpair" and optvalue not in self.btfx_symbols:
            msgtext = f"incorect symbol , available pairs are {self.btfx_symbols}"
            bot.send_message(chat_id, text=msgtext, parse_mode='HTML')
            return

        if optname == "graphtheme" and optvalue not in ['standard', 'colorblind', 'monochrome']:
            msgtext = f"incorect theme , available themes are standard, colorblind, monochrome"
            bot.send_message(chat_id, text=msgtext, parse_mode='HTML')
            return

        self.userdata[chat_id][optname] = optvalue
        bgu_save_userdata(self.userdata)

        message = f'<pre>option {optname} was set to {optvalue}</pre>'
        bot.send_message(chat_id, text=message, parse_mode='HTML')



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
        bgu_save_userdata(self.userdata)


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

        if  not bgu_isnumber(volume):
            msgtext = f"incorect volume , {volume} is not a number"
            bot.send_message(chat_id, text=msgtext)
            return

        if  not bgu_isnumber(price):
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

    def cb_btn_cancel_order(self, bot, update):
        query = update.callback_query
        update.callback_query.answer()
        chat_id = update.callback_query.message.chat.id
        LOGGER.info(f"i got {query.data} from {chat_id}")

        order_id = int(query.data.split(':')[1])
        LOGGER.info(f"orderid : {order_id}")

        del_order = self.btfx_client.delete_order(order_id)
        LOGGER.info(f"del_order : {del_order}")


    def cb_wss_auth(self, message, *args, **kwargs):
        if not isinstance(message, list):
            LOGGER.info(message)
            return

        types = {
            'on' : self.on_notification,
            'oc' : self.oc_notification
        }
        LOGGER.info(message)
        LOGGER.info(f"msg type is : {message[1]}")
        msg_type = message[1]
        if msg_type in types.keys():
            types[msg_type](message)



    def on_notification(self, message):
        order_id = message[2][0]
        order_symbol = message[2][3][1:]
        order_volume = message[2][6]
        order_type = message[2][8]
        order_price = message[2][16]
        plus_sign = "+" if order_volume > 0 else ""
        lines = []
        lines.append("<pre>")
        lines.append(f"Order {order_id} {order_symbol} {order_type} ")
        lines.append(f"{plus_sign}{order_volume} @ {order_price} PLACED")
        lines.append("</pre>")
        composed_message = ''.join(lines)
        LOGGER.info(composed_message)

        #send message to everyone who is authenticated
        for key, value in self.userdata.items():
            if value['authenticated'] == "yes":
                try:
                    self.tbot.send_message(key, text=composed_message, parse_mode='HTML')
                except (TimedOut, TelegramError):
                    LOGGER.error(f"coult not send message to {key}")

    def oc_notification(self, message):
        order_id = message[2][0]
        order_symbol = message[2][3][1:]
        order_volume = message[2][6] if message[2][13] == "CANCELED" else message[2][7]
        order_type = message[2][8]
        order_status = message[2][13]
        order_price = message[2][16]
        plus_sign = "+" if order_volume > 0 else ""
        lines = []
        lines.append("<pre>")
        lines.append(f"Order {order_id} {order_symbol} {order_type} ")
        lines.append(f"{plus_sign}{order_volume} @ {order_price} was {order_status}")
        lines.append("</pre>")
        composed_message = ''.join(lines)
        LOGGER.info(composed_message)

        #send message to everyone who is authenticated
        for key, value in self.userdata.items():
            if value['authenticated'] == "yes":
                try:
                    self.tbot.send_message(key, text=composed_message, parse_mode='HTML')
                except (TimedOut, TelegramError):
                    LOGGER.error(f"coult not send message to {key}")
