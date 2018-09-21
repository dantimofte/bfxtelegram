#!/usr/bin/env python3
"""
Module Docstring
"""

import logging
# telegram libraries
from telegram.ext import Updater
from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import (TelegramError, TimedOut)
# bitfinex libraries
from bitfinex import ClientV1 as Client
from bitfinex import ClientV2 as Client2

from bfxtelegram.bfxwss import Bfxwss
from bfxtelegram import utils
from bfxtelegram.tgraph import Tgraph

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


def ensure_authorized(passed_function):
    def wrapper(self, bot, update, *args, **kwargs):
        chat_id = update.message.chat.id
        if chat_id not in self.userdata:
            LOGGER.info("chat id not found in list of chats")
            message = "<pre>Please authenticate</pre>"
            bot.send_message(chat_id, text=message, parse_mode='HTML')
            return
        authenticated = self.userdata[chat_id]['authenticated']
        if authenticated == "no":
            LOGGER.info("user id not authenticated")
            message = "<pre>Please authenticate</pre>"
            bot.send_message(chat_id, text=message, parse_mode='HTML')
            return
        return passed_function(self, bot, update, *args, **kwargs)
    return wrapper


class Btfxbot:
    def __init__(self, telegram_token, auth_pass, btfx_key, btfx_secret):
        LOGGER.info("Here be dragons")
        self.userdata = utils.read_userdata()
        self.auth_pass = auth_pass
        self.btfx_client = Client(btfx_key, btfx_secret)
        self.btfx_client2 = Client2(btfx_key, btfx_secret)
        self.btfx_symbols = self.btfx_client.symbols()

        updater = Updater(telegram_token)
        self.tbot = updater.bot
        self.btfxwss = Bfxwss(self.send_to_users, key=btfx_key, secret=btfx_secret)
        # Get the dispatcher to register handlers
        qdp = updater.dispatcher
        # on different commands - answer in Telegram
        qdp.add_handler(CommandHandler("start", self.cb_start))
        qdp.add_handler(CommandHandler("graph", self.cb_graph, pass_args=True))
        qdp.add_handler(CommandHandler("auth", self.cb_auth, pass_args=True))
        qdp.add_handler(CommandHandler("option", self.cb_option, pass_args=True))
        qdp.add_handler(CommandHandler("neworder", self.cb_new_order, pass_args=True))
        qdp.add_handler(CommandHandler("orders", self.cb_orders, pass_args=True))
        qdp.add_handler(CommandHandler("calc", self.cb_calc, pass_args=True))
        qdp.add_handler(CommandHandler("help", self.cb_help, pass_args=True))
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

    # CALLBACK FUNCTIONS
    def cb_start(self, bot, update):
        """
            Callback method used to check if bot is running
            Sends a telegramm message
        """
        update.message.reply_text('Here be Dragons')

    def cb_auth(self, bot, update, args):
        """
            Callback method used to authenticate to the bot
            Sends a telegramm message
        """
        chat_id = update.message.chat.id
        username = update.message.chat.username
        first_name = update.message.chat.first_name
        last_name = update.message.chat.last_name
        LOGGER.info(f"{chat_id} {username} : /auth {args}")
        if len(args) < 1:
            self.send_help(chat_id, "auth")
            return

        botpass = args[0]
        if chat_id in self.userdata:
            userinfo = self.userdata[chat_id]
        else:
            userinfo = {"authenticated": "no", "failed_auth": 0}

        # ignore user if he keeps forcing /auth
        if userinfo['failed_auth'] > 20:
            return

        # notify user that there have been to many failed atempts
        if userinfo['failed_auth'] > 10:
            bot.send_message(chat_id, text="you are blocked")
            userinfo["failed_auth"] += 1
            self.userdata[chat_id] = userinfo
            utils.save_userdata(self.userdata)
            return

        if botpass == self.auth_pass:
            message = "<pre>authentication successfull </pre>"
            bot.send_message(chat_id, text=message, parse_mode='HTML')
            userinfo["authenticated"] = "yes"
            userinfo["failed_auth"] = 0
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
        utils.save_userdata(self.userdata)

    def cb_error(self, bot, update, boterror):
        """Log Errors caused by Updates."""
        LOGGER.warning(f'Update "{update}" caused error "{boterror}"')

    @ensure_authorized
    def cb_graph(self, bot, update, args):
        LOGGER.info(f"{update.message.chat.username} : /graph {args}")
        chat_id = update.message.chat.id

        if 'defaultpair' in self.userdata[chat_id]:
            defaultpair = self.userdata[chat_id]['defaultpair']
        else:
            defaultpair = "iotusd"
        symbol = args[0] if args else defaultpair

        if symbol not in self.btfx_symbols:
            symbols = " ".join(self.btfx_symbols)
            msgtext = f"incorect symbol , available pairs are {symbols}"
            bot.send_message(chat_id, text=msgtext, parse_mode='HTML')
            return

        tradepair = f"t{symbol.upper()}"

        chat_id = update.message.chat.id
        candles_data = self.btfx_client2.candles("1h", tradepair, "hist", limit='120')
        active_orders = self.btfx_client.active_orders()
        order_book = self.btfx_client.order_book(
            "iotusd",
            parameters={"limit_bids": 800, "limit_asks": 800}
        )

        if 'graphtheme' in self.userdata[chat_id]:
            graphtheme = self.userdata[chat_id]['graphtheme']
        else:
            graphtheme = "normal"

        orders_data = order_book['asks'] + order_book['bids']
        newgraph = Tgraph(candles_data, active_orders, orders_data, symbol, graphtheme=graphtheme)
        newgraph.save_picture()
        bot.send_photo(chat_id=chat_id, photo=open('graph.png', 'rb'))
        del newgraph

    @ensure_authorized
    def cb_option(self, bot, update, args):
        LOGGER.info(f"{update.message.chat.username} : /option {args}")
        chat_id = update.message.chat.id

        if len(args) < 2:
            self.send_help(chat_id, "option")
            return

        optname = args[0]
        optvalue = args[1]
        valid_options = ['defaultpair', 'graphtheme', 'calctype']
        if optname not in valid_options:
            str_options = " ".join(valid_options)
            formated_message = (
                "<pre>"
                f"{optname} is not a valid option\n"
                f"valid options are {str_options}\n"
                "</pre>"
            )
            bot.send_message(chat_id, text=formated_message, parse_mode='HTML')
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
        utils.save_userdata(self.userdata)

        message = f'<pre>option {optname} was set to {optvalue}</pre>'
        bot.send_message(chat_id, text=message, parse_mode='HTML')

    # Bitfinex Rest Methods
    @ensure_authorized
    def cb_new_order(self, bot, update, args):
        LOGGER.info(f"{update.message.chat.username} : /neworder {args}")
        chat_id = update.message.chat.id

        # Verify order parameters
        if len(args) < 4:
            self.send_help(chat_id, "neworder")
            return

        volume = args[0]
        price = args[1]
        tradepair = args[2]
        tradetype = args[3]

        if not utils.isnumber(volume):
            bot.send_message(chat_id, text=f"incorect volume , {volume} is not a number")
            return

        if not utils.isnumber(price):
            bot.send_message(chat_id, text=f"incorect price , {price} is not a number")
            return

        if tradepair not in self.btfx_symbols:
            msgtext = f"incorect tradepair , available pairs are {self.btfx_symbols}"
            bot.send_message(chat_id, text=msgtext, parse_mode='HTML')
            return

        if tradetype not in utils.REST_TYPES:
            types = " ".join(utils.REST_TYPES)
            msgtext = f"incorect tradetype , available types are : {types}"
            bot.send_message(chat_id, text=msgtext, parse_mode='HTML')
            return

        side = 'buy' if float(volume) > 0 else 'sell'
        volume = abs(float(volume))
        neworder = self.btfx_client.place_order(
            str(volume),
            price,
            side,
            utils.REST_TYPES[tradetype],
            symbol=tradepair
        )

        if 'message' in neworder:
            bot.send_message(chat_id, text=neworder['message'])
            return

        orderid = neworder['id']
        buttons = [
            # InlineKeyboardButton('Update Price', callback_data=f"neworder:updprice:{orderid}"),
            # InlineKeyboardButton('Update Volume', callback_data=f"neworder:updvolume:{orderid}"),
            InlineKeyboardButton('Cancel order', callback_data=f"cancel_order:{orderid}")
        ]
        keyboard = InlineKeyboardMarkup([buttons])

        formated_message = f"Order {orderid} placed succesfully\n"

        try:
            update.message.reply_text(formated_message, reply_markup=keyboard)
        except(TimedOut, TelegramError) as error:
            LOGGER.info(f"coult not send message keyboard to {chat_id}")
            LOGGER.info(error)

    @ensure_authorized
    def cb_calc(self, bot, update, args):
        LOGGER.info(f"{update.message.chat.username} : /calc {args}")
        chat_id = update.message.chat.id

        if len(args) < 1 and 'calctype' not in self.userdata[chat_id]:
            self.send_help(chat_id, "calc")
            return

        if 'calctype' in self.userdata[chat_id]:
            default_type = self.userdata[chat_id]['calctype']

        calctype = args[0] if args else default_type
        self.btfxwss.calc([calctype])

    @ensure_authorized
    def cb_orders(self, bot, update, args):
        LOGGER.info(f"{update.message.chat.username} : /orders {args}")
        chat_id = update.message.chat.id

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

    @ensure_authorized
    def cb_help(self, bot, update, args):
        LOGGER.info(f"{update.message.chat.username} : /help {args}")
        chat_id = update.message.chat.id
        help_key = args[0] if args else "none"
        self.send_help(chat_id, help_key)

    def cb_btn_orders(self, bot, update):
        query = update.callback_query
        update.callback_query.answer()
        chat_id = update.callback_query.message.chat.id
        LOGGER.info(f"i got {query.data} from {chat_id}")

        orders_type = query.data.split(':')[1]
        LOGGER.info(f"orders_type : {orders_type}")

        active_orders = self.btfx_client.active_orders()
        if orders_type == "margin":
            orders_list = [order for order in active_orders if 'exchange' not in order['type']]
        else:
            orders_list = [order for order in active_orders if 'exchange' in order['type']]
        if not orders_list:
            msgtext = f"no active {orders_type} orders found"
            bot.send_message(chat_id, text=msgtext, parse_mode='HTML')
            return

        for order in orders_list:
            order_id = order['id']
            symbol = order['symbol']
            side = order['side']
            original_amount = order['original_amount']
            remaining_amount = order['remaining_amount']
            price = order['price']
            formated_message = (
                f"{order_id}: {symbol} {side} {remaining_amount}@{price} "
                f"original amount : {original_amount}"
            )
            buttons = [InlineKeyboardButton('cancel', callback_data=f'cancel_order:{order_id}')]
            keyboard = InlineKeyboardMarkup([buttons])
            try:
                bot.send_message(chat_id, text=formated_message, reply_markup=keyboard)
            except (TimedOut, TelegramError) as error:
                print(f"could not send message {formated_message} to {chat_id}")
                print(error)

    def cb_btn_cancel_order(self, bot, update):
        query = update.callback_query
        update.callback_query.answer()
        chat_id = update.callback_query.message.chat.id
        LOGGER.info(f"i got {query.data} from {chat_id}")

        order_id = int(query.data.split(':')[1])
        LOGGER.info(f"orderid : {order_id}")

        del_order = self.btfx_client.delete_order(order_id)
        if 'message' in del_order:
            bot.send_message(chat_id, text=del_order['message'])

        LOGGER.info(f"del_order : {del_order}")

    def send_to_users(self, message):
        for key, value in self.userdata.items():
            if value['authenticated'] == "yes":
                try:
                    self.tbot.send_message(key, text=message, parse_mode='HTML')
                except (TimedOut, TelegramError):
                    LOGGER.error(f"coult not send message to {key}")

    def send_help(self, chat_id, help_key):
        helps = " ".join(utils.CMDHELP.keys())
        formated_message = f"<pre>help is available for : {helps}</pre>"
        if help_key not in utils.CMDHELP:
            self.tbot.send_message(chat_id, text=formated_message, parse_mode='HTML')
            return
        self.tbot.send_message(chat_id, text=utils.CMDHELP[help_key], parse_mode='HTML')
