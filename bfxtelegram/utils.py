#!/usr/bin/env python3
"""
MIT License

Copyright (c) 2018 Timofte Dan

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
        "Or specify a default calculation using /option"
        "</pre>"
    )
}


WS_MSG_TYPES = [
    'bu', 'ps', 'pn', 'pu', 'pc', 'ws', 'wu', 'os', 'on', 'on-req', 'ou', 'oc', 'oc-req',
    'oc_multi-req', 'te', 'tu', 'fte', 'ftu', 'hos', 'mis', 'miu', 'n', 'fos', 'fon', 'fou', 'foc',
    'hfos', 'fcs', 'fcn', 'fcu', 'fcc', 'hfcs', 'fls', 'fln', 'flu', 'flc', 'hfls', 'hfts', 'hb',
    'uca'
]


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
    files = glob.glob('data/usersdata.pickle')
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
    userdata_file = "data/usersdata.pickle"
    ensure_dir(userdata_file)
    with open(userdata_file, 'wb') as outfile:
        pickle.dump(userdata, outfile)
    human_readable_file = "data/usersdata.json"
    with open(human_readable_file, 'w') as outfile:
        json.dump(userdata, outfile)
