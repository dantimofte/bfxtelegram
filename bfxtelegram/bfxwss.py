#!/usr/bin/env python3
"""
Module Docstring
"""
import logging
import threading
from bitfinex import WssClient
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

class  Bfxwss(WssClient):
    def __init__(self, bot, send_to_users, key="", secret=""):
        super().__init__(key=key, secret=secret)
        self.tbot = bot
        self.send_to_users = send_to_users
        self.connection_timer = None
        self.connection_timeout = 15
        self.authenticate(self._cb_wss_auth)
        self.start()

    def _stop_timers(self):
        """Stops connection timers."""
        if self.connection_timer:
            self.connection_timer.cancel()
        LOGGER.info("_stop_timers(): Timers stopped.")

    def _start_timers(self):
        """Resets and starts timers for API data and connection."""
        LOGGER.info("_start_timers(): Resetting timers..")
        self._stop_timers()
        # Automatically reconnect if we didnt receive data
        self.connection_timer = threading.Timer(self.connection_timeout, self._connection_timed_out)
        self.connection_timer.start()


    def _connection_timed_out(self):
        """Issues a reconnection if the connection timed out.
        :return:
        """
        LOGGER.info("_connection_timed_out(): Fired! Issuing reconnect..")
        self.close()
        self.authenticate(self._cb_wss_auth)

    def _cb_heartbeat_handler(self, *args):
        self._start_timers()

    def _cb_wss_auth(self, message, *args, **kwargs):
        if not isinstance(message, list):
            LOGGER.info(message)
            return

        types = {
            'on' : self._cb_on_notification,
            'oc' : self._cb_oc_notification,
            'hb' : self._cb_heartbeat_handler,
            'pu' : self._cb_pu_notification
        }
        LOGGER.info(message)
        LOGGER.info(f"msg type is : {message[1]}")
        msg_type = message[1]
        if msg_type in types.keys():
            types[msg_type](message)


    def _cb_on_notification(self, message):
        order_id = message[2][0]
        order_symbol = message[2][3][1:]
        order_volume = message[2][6]
        order_type = message[2][8]
        order_price = message[2][16]
        plus_sign = "+" if order_volume > 0 else ""

        formated_message = (
            "<pre>"
            f"Order {order_id} {order_symbol} {order_type} "
            f"{plus_sign}{order_volume} @ {order_price} PLACED"
            "</pre>"
        )
        #send message to everyone who is authenticated
        self.send_to_users(formated_message)

    def _cb_oc_notification(self, message):
        order_id = message[2][0]
        order_symbol = message[2][3][1:]
        order_volume = message[2][6] if message[2][13] == "CANCELED" else message[2][7]
        order_type = message[2][8]
        order_status = message[2][13]
        order_price = message[2][16]
        plus_sign = "+" if order_volume > 0 else ""

        formated_message = (
            "<pre>"
            f"Order {order_id} {order_symbol} {order_type} "
            f"{plus_sign}{order_volume} @ {order_price} was {order_status}"
            "</pre>"
        )

        #send message to everyone who is authenticated
        self.send_to_users(formated_message)


    def _cb_pu_notification(self, message):
        if not all(message[2]):
            return

        formated_message = (
            "<pre>"
            f"Pair         : {message[2][0]}\n"
            f"Amount       : {message[2][2]}\n"
            f"Base Price   : {message[2][3]}\n"
            f"Funding Cost : {message[2][4]}\n"
            f"Profit/Loss  : {message[2][6]} {message[2][7]}%\n"
            f"Liquidation  : {message[2][8]}\n"
            f"Leverage     : {message[2][9]} "
            "</pre>"
        )
        #send message to everyone who is authenticated
        self.send_to_users(formated_message)
