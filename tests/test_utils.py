# W0613:Unused argument
# C0103:Method name too long
# pylint: disable=W0613,C0103

import glob
import unittest
from bfxtelegram import utils
from tests.conftest import BTFX_SYMBOLS, CURRENCIES, BALANCES


class UtilsTests(unittest.TestCase):
    def test_isnumber(self):
        self.assertTrue(
            utils.isnumber("100.4")
        )

        self.assertFalse(
            utils.isnumber("100.a")
        )

    def test_ensure_dir(self):
        self.assertIsNone(
            utils.ensure_dir("tests/__pycache__")
        )

    def test_read_userdata(self):
        userdata = utils.read_userdata()
        self.assertIsInstance(userdata, dict)

    def test_save_userdata(self):
        userdata = utils.read_userdata()
        self.assertIsNone(
            utils.save_userdata(userdata)
        )
        self.assertTrue(
            glob.glob('data/usersdata.pickle')
        )
        self.assertTrue(
            glob.glob('data/usersdata.json')
        )

    def test_get_currencies(self):
        self.assertIsInstance(
            utils.get_currencies(BTFX_SYMBOLS),
            list
        )

        self.assertIn(
            "btc",
            utils.get_currencies(BTFX_SYMBOLS)
        )

        self.assertNotIn(
            "blabla",
            utils.get_currencies(BTFX_SYMBOLS)
        )

    def test_format_balance(self):
        self.assertTrue(
            utils.format_balance(CURRENCIES, BALANCES)
        )

        self.assertIn(
            "iot",
            utils.format_balance(CURRENCIES, BALANCES)
        )
