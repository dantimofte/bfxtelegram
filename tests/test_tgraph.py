
# pylint: disable-msg=C0103
import unittest
from bfxtelegram.tgraph import Tgraph
from tests.conftest import CANDLES_DATA, ACTIVE_ORDERS, ORDERBOOK_DATA, SYMBOL


class TgraphTests(unittest.TestCase):

    def setUp(self):
        self.cgraph = Tgraph(CANDLES_DATA, ACTIVE_ORDERS, ORDERBOOK_DATA, SYMBOL)

    def test_invalid_token(self):
        self.assertTrue(SYMBOL)
