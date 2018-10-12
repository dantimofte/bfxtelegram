#!/usr/bin/env python3
"""
MIT License

Copyright (c) 2018 Dan Timofte

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import os
import re
import glob
import json
import pickle
import logging
from decimal import Decimal
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

REST_TYPES = {
    "mmarket": "market",
    "mlimit": "limit",
    "mstop": "stop",
    "mtrail": "trailing-stop",
    "mfok": "fill-or-kill",
    "emarket": "exchange market",
    "elimit": "exchange limit",
    "estop": "exchange stop",
    "etrail": "exchange trailing-stop",
    "efok": "exchange fill-or-kill"
}

CMDHELP = {
    "set": (
        "<pre>"
        "/set defaultpair symbol\n"
        "  symbols : iotusd, btcusd, ltcusd, ethusd\n"
        "/set graphtheme theme\n"
        "  themes : standard, colorblind, monochrome\n"
        "/set calctype type\n"
        "  ex : /set calctype position_tIOTUSD\n"
        "/set getbalance currencie\n"
        "  ex : /set getbalance iot usd btc eth\n"
        "</pre>"
    ),
    "auth": (
        "<pre>"
        "please run /auth password\n"
        "AUTH_PASS set in the .env file"
        "</pre>"
    ),
    "neworder": (
        "<pre>"
        "New order is placed like this : \n"
        "/neworder ±volume price tradepair tradetype\n"
        "/neworder -100 4.00 iotusd elimit"
        "</pre>"
    ),
    "calc": (
        "<pre>"
        "Calculations are requested with the command : /calc type\n"
        "Possible prefixes:\n"
        "    margin_sym_SYMBOL\n"
        "    funding_sym_SYMBOL\n"
        "    position_SYMBOL\n"
        "    wallet_WALLET-TYPE_CURRENCY\n"
        "Or specify a default calculation using /set"
        "</pre>"
    ),
    "newalert": (
        "<pre>"
        "New Alert is placed like this : \n"
        "/neworder symbol price\n"
        "/neworder iotusd 4.00"
        "</pre>"
    ),
    "graph": (
        "<pre>"
        "This return a picture containing the hourly candle chart"
        "Please give a valid trading pair for which  you want the graphic or set a default one "
        "using :\n/set defaultpair iotusd\n"
        "example :\n/graph \n/graph iotusd"
        "<pre>"
    ),
    "getbalance": (
        "<pre>"
        "getbalance will return a list of balances for the currencies you set using /set\n"
        "example : /set getbalance iot usd btc\n"
        "example : /getbalance\n"
        "</pre>"
    )
}


WS_MSG_TYPES = [
    'bu', 'ps', 'pn', 'pu', 'pc', 'ws', 'wu', 'os', 'on', 'on-req', 'ou', 'oc', 'oc-req',
    'oc_multi-req', 'te', 'tu', 'fte', 'ftu', 'hos', 'mis', 'miu', 'n', 'fos', 'fon', 'fou', 'foc',
    'hfos', 'fcs', 'fcn', 'fcu', 'fcc', 'hfcs', 'fls', 'fln', 'flu', 'flc', 'hfls', 'hfts', 'hb',
    'uca', 'ou-req', 'wallet_transfer'
]

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def isnumber(pnumber):
    num_format = re.compile(r"^[\-]?[0-9]*\.?[0-9]*$")
    if re.match(num_format, pnumber):
        return True

    return False


def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def read_userdata():
    userdata_file = os.path.join(ROOT_DIR, 'data/usersdata.pickle')
    files = glob.glob(userdata_file)
    if not files:
        return {}
    with open(files[0], 'rb') as usersdata_file:
        try:
            pickle_object = pickle.load(usersdata_file)
        except (ValueError, TypeError):
            print(f'error on parsing pickle {ValueError} # {TypeError}')
            return {}
        return pickle_object


def save_userdata(userdata):
    userdata_file = os.path.join(ROOT_DIR, 'data/usersdata.pickle')
    human_readable_file = os.path.join(ROOT_DIR, 'data/usersdata.json')
    ensure_dir(userdata_file)
    with open(userdata_file, 'wb') as outfile:
        pickle.dump(userdata, outfile)
    with open(human_readable_file, 'w') as outfile:
        json.dump(userdata, outfile)


def get_currencies(btfx_symbols):
    """
        Extract all currencies from the list of tradepairs available on bitfinex
        returns a list
    """
    currencies = []
    for symbol in btfx_symbols:
        currencies.append(symbol[:3])
        currencies.append(symbol[3:])
    currencies = list(set(currencies))
    return currencies


def format_balance(currencies, balances):
    # remove balance for currencies not in users list
    balances = [balance for balance in balances if balance['currency'] in currencies]
    # determine max width for each column
    width_eamt = max([len(bal['amount']) for bal in balances if bal['type'] == 'exchange'])
    width_eavl = max([len(bal['available']) for bal in balances if bal['type'] == 'exchange'])
    width_tamt = max([len(bal['amount']) for bal in balances if bal['type'] == 'trading'])
    width_tavl = max([len(bal['available']) for bal in balances if bal['type'] == 'trading'])
    width_damt = max([len(bal['amount']) for bal in balances if bal['type'] == 'deposit'])
    width_davl = max([len(bal['available']) for bal in balances if bal['type'] == 'deposit'])

    # initialize dictionary from which lines will be obtained
    bal_dict = {}
    for currency in currencies:
        bal_dict[currency] = {
            "exchange": {"amount": "0.0", "available": "0.0"},
            "trading": {"amount": "0.0", "available": "0.0"},
            "deposit": {"amount": "0.0", "available": "0.0"}
        }

    # update values with real values from balances
    for balance in balances:
        currency = balance['currency']
        ctype = balance['type']
        bal_dict[currency][ctype]["amount"] = balance["amount"]
        bal_dict[currency][ctype]["available"] = balance["available"]

    # build formated message
    lines = []
    width_exchange = width_eamt + width_eavl + 4
    width_trading = width_tamt + width_tavl + 5
    width_deposit = width_damt + width_davl + 4
    header_line = (
        "      "
        f"{'exchange':^{width_exchange}}"
        "||"
        f"{'margin':^{width_trading}}"
        "||"
        f"{'funding':^{width_deposit}}"
        "\n"
    )
    lines.append(header_line)
    for curr, val in bal_dict.items():
        eamt = Decimal(val['exchange']['amount'])
        eavl = Decimal(val['exchange']['available'])
        tamt = Decimal(val['trading']['amount'])
        tavl = Decimal(val['trading']['available'])
        damt = Decimal(val['deposit']['amount'])
        davl = Decimal(val['deposit']['available'])
        line = (
            f"{curr}   "
            f"{eamt:{width_eamt}} : {eavl:{width_eavl}} || "
            f"{tamt:{width_tamt}} : {tavl:{width_tavl}} || "
            f"{damt:{width_damt}} : {davl:{width_davl}}\n"
        )
        lines.append(line)

    balances_message = "".join(lines)
    return balances_message
