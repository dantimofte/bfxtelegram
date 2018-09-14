#!/usr/bin/env python3
"""
Module Docstring
source : https://github.com/Crypto-toolbox/btfxwss/blob/master/btfxwss/connection.py
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
        self.authenticate(self._auth_messages)
        self.start()

    def _stop_timers(self):
        """Stops connection timers."""
        if self.connection_timer:
            self.connection_timer.cancel()
        LOGGER.info("_stop_timers() : Timers stopped.")

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
        self.reconnect()

    def _heartbeat_handler(self):
        LOGGER.info("_hb_handler()  : new heart beat")
        self._start_timers()


    def _system_handler(self, data):
        """Distributes system messages to the appropriate handler.
        System messages include everything that arrives as a dict,
        """
        LOGGER.debug(f"_system_handler(): Received a system message: {data}")
        event = data.pop('event')
        if event == 'info':
            LOGGER.info(f"_system_handler(): Distributing {data} to _info_handler..")
            self._info_handler(data)
        else:
            LOGGER.error("Unhandled event: %s, data: %s", event, data)

    def _info_handler(self, data):
        """
        Handle INFO messages from the API and issues relevant actions.
        """

        if 'code' not in data and 'version' in data:
            LOGGER.info(f"Initialized Client on API Version {data['version']}")
            return

        info_message = {
            20000: 'Invalid User given! Please make sure the given ID is correct!',
            20051: 'Stop/Restart websocket server (please try to reconnect)',
            20060: 'Refreshing data from the trading engine; please pause any acivity.',
            20061: 'Done refreshing data from the trading engine. Re-subscription advised.'
        }

        codes = {20051: self.reconnect, 20060: self.pause, 20061: self.unpause}

        if 'version' in data:
            LOGGER.info(f"API version: {data['version']}")
            return

        try:
            LOGGER.info(info_message[data['code']])
            codes[data['code']]()
        except KeyError as exception:
            LOGGER.exception(exception)
            LOGGER.error(f"Unknown Info code {data['code']}!")
            raise



    def _auth_messages(self, data):
        # Handle data
        if isinstance(data, dict):
            self._system_handler(data)
        else:
            # This is a list of data
            if data[1] == 'hb':
                self._heartbeat_handler()
            else:
                self._data_handler(data)



    def _data_handler(self, data):
        # Pass the data up to the Client
        LOGGER.debug(f"_data_handler(): Passing {data} to client..")

        types = {
            'on' : self._on_notification,
            'oc' : self._oc_notification,
            'hb' : self._heartbeat_handler,
            'pu' : self._pu_notification
        }
        LOGGER.info(data)
        msg_type = data[1]
        if msg_type in types.keys():
            types[msg_type](data)

    def _on_notification(self, message):
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

    def _oc_notification(self, message):
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


    def _pu_notification(self, message):
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

    def reconnect(self):
        self.close()
        self.authenticate(self._auth_messages)

    def pause(self):
        self.close()
        self._stop_timers()

    def unpause(self):
        self.authenticate(self._auth_messages)
        self._start_timers()
