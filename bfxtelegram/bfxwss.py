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


class Bfxwss(WssClient):
    def __init__(self, send_to_users, key="", secret=""):
        self.msg_type_func = {
            'bu': self._send_bu_msg,
            'ps': self._send_ps_msg,
            'pn': self._send_pn_msg,
            'pu': self._send_pu_msg,
            'pc': self._send_pc_msg,
            'ws': self._send_ws_msg,
            'wu': self._send_wu_msg,
            'os': self._send_os_msg,
            'on': self._send_on_msg,
            'on-req': self._send_onreq_msg,
            'ou': self._send_ou_msg,
            'oc': self._send_oc_msg,
            'oc-req': self._send_ocreq_msg,
            'oc_multi-req': self._send_ocmultireq_msg,
            'te': self._send_te_msg,
            'tu': self._send_tu_msg,
            'fte': self._send_fte_msg,
            'ftu': self._send_ftu_msg,
            'hos': self._send_hos_msg,
            'mis': self._send_mis_msg,
            'miu': self._send_miu_msg,
            'n': self._send_n_msg,
            'fos': self._send_fos_msg,
            'fon': self._send_fon_msg,
            'fou': self._send_fou_msg,
            'foc': self._send_foc_msg,
            'hfos': self._send_hfos_msg,
            'fcs': self._send_fcs_msg,
            'fcn': self._send_fcn_msg,
            'fcu': self._send_fcu_msg,
            'fcc': self._send_fcc_msg,
            'hfcs': self._send_hfcs_msg,
            'fls': self._send_fls_msg,
            'fln': self._send_fln_msg,
            'flu': self._send_flu_msg,
            'flc': self._send_flc_msg,
            'hfls': self._send_hfls_msg,
            'hfts': self._send_hfts_msg,
            'uca': self._send_uca_msg,
            'hb': self._heartbeat_handler,
            'ou-req': self._send_oureq_msg,
            'wallet_transfer': self._send_wallettransfer_msg
        }

        super().__init__(key=key, secret=secret)
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
        """
            bu           : balance update
            ps           : position snapshot
            pn           : new position
            pu           : position update
            pc           : position close
            ws           : wallet snapshot
            wu           : wallet update
            os           : order snapshot
            on           : new order
            on-req       : new order request
            ou           : order update
            oc           : order cancel
            oc-req       : order cancel request
            oc_multi-req : multiple orders cancel request
            te           : trade executed
            tu           : trade execution update
            fte          : funding trade execution
            ftu          : funding trade update
            hos          : historical order snapshot
            mis          : margin information snapshot
            miu          : margin information update
            n            : notification
            fos          : funding offer snapshot
            fon          : funding offer new
            fou          : funding offer update
            foc          : funding offer cancel
            hfos         : historical funding offer snapshot
            fcs          : funding credits snapshot
            fcn          : funding credits new
            fcu          : funding credits update
            fcc          : funding credits close
            hfcs         : historical funding credits snapshot
            fls          : funding loan snapshot
            fln          : funding loan new
            flu          : funding loan update
            flc          : funding loan close
            hfls         : historical funding loan snapshot
            hfts         : historical funding trade snapshot
            uac          : user custom price alert
        """
        LOGGER.debug(f"_data_handler(): Passing {data} to client..")
        LOGGER.info(data)
        msg_type = data[1]
        if msg_type in self.msg_type_func.keys():
            self.msg_type_func[msg_type](msg_type, data)

    def _send_bu_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_ps_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_pn_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_pu_msg(self, msg_type, message):
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
        # send message to everyone who is authenticated
        self.send_to_users(msg_type, formated_message)

    def _send_pc_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_ws_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_wu_msg(self, msg_type, message):
        wtype = message[2][0]
        coin = message[2][1]
        balance = message[2][2]
        formated_message = (
            "<pre>"
            f"{msg_type} msg\n"
            f"{coin} {wtype} wallet updated,  new balance is {balance}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_os_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_on_msg(self, msg_type, message):
        order_id = message[2][0]
        order_symbol = message[2][3][1:]
        order_volume = message[2][6]
        order_type = message[2][8]
        order_price = message[2][16]
        plus_sign = "+" if order_volume > 0 else ""

        formated_message = (
            "<pre>"
            f"{msg_type} msg\n"
            f"Order {order_id} {order_symbol} {order_type} "
            f"{plus_sign}{order_volume} @ {order_price} PLACED"
            "</pre>"
        )
        # send message to everyone who is authenticated
        self.send_to_users(msg_type, formated_message)

    def _send_onreq_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} msg\n"
            f"{message[2][7]}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_ou_msg(self, msg_type, message):
        order_id = message[2][0]
        order_symbol = message[2][3][1:]
        order_volume = message[2][6]
        order_type = message[2][8]
        order_price = message[2][16]
        plus_sign = "+" if order_volume > 0 else ""

        formated_message = (
            "<pre>"
            f"{msg_type} msg\n"
            f"Order {order_id} updated : {order_symbol} {order_type} "
            f"{plus_sign}{order_volume} @ {order_price}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_oc_msg(self, msg_type, message):
        order_id = message[2][0]
        order_symbol = message[2][3][1:]
        order_volume = message[2][6] if message[2][13] == "CANCELED" else message[2][7]
        order_type = message[2][8]
        order_status = message[2][13]
        order_price = message[2][16]
        plus_sign = "+" if order_volume > 0 else ""

        formated_message = (
            "<pre>"
            f"{msg_type} msg\n"
            f"Order {order_id} {order_symbol} {order_type} "
            f"{plus_sign}{order_volume} @ {order_price} was {order_status}"
            "</pre>"
        )

        # send message to everyone who is authenticated
        self.send_to_users(msg_type, formated_message)

    def _send_ocreq_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} msg\n"
            f"{message[2][7]}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_ocmultireq_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_te_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_tu_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_fte_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_ftu_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_hos_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_mis_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_miu_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_n_msg(self, msg_type, message):
        new_type = message[2][1]
        if new_type in self.msg_type_func:
            self.msg_type_func[new_type](new_type, message)
        else:
            formated_message = (
                "<pre>"
                f"n message is : {message}"
                "</pre>"
            )
            self.send_to_users(msg_type, formated_message)

    def _send_fos_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_fon_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_fou_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_foc_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_hfos_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_fcs_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_fcn_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_fcu_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_fcc_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_hfcs_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_fls_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_fln_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_flu_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_flc_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_hfls_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_hfts_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} message is : {message}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_uca_msg(self, msg_type, message):
        print(f"uca is {message}")
        message = message[2][4]
        direction = "under" if message[5] < 0 else "above"
        expires = message[4]
        price = message[3]
        pair = message[2][1:]
        formated_message = f"<pre>{pair} went {direction} {price} alert expires in {expires}</pre>"
        self.send_to_users(msg_type, formated_message)

    def _send_oureq_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} msg\n"
            f"{message[2][7]}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def _send_wallettransfer_msg(self, msg_type, message):
        formated_message = (
            "<pre>"
            f"{msg_type} msg\n"
            f"{message[2][7]}"
            "</pre>"
        )
        self.send_to_users(msg_type, formated_message)

    def reconnect(self):
        LOGGER.info(f"reconnect(): started")
        self.close()
        LOGGER.info(f"reconnect(): closed finished")
        self.authenticate(self._auth_messages)
        LOGGER.info(f"reconnect(): authenticate finished")
        self._start_timers()
        LOGGER.info(f"reconnect(): timers started")

    def pause(self):
        self.close()
        self._stop_timers()

    def unpause(self):
        self.authenticate(self._auth_messages)
        self._start_timers()
