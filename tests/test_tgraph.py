# pylint: disable-msg=C0103
import unittest
import glob
import pandas as pd
from bokeh.plotting.figure import Figure
from bfxtelegram.tgraph import Tgraph
from tests.conftest import CANDLES_DATA, ACTIVE_ORDERS, ORDERBOOK_DATA, SYMBOL


class TgraphTests(unittest.TestCase):

    def setUp(self):
        self.cgraph = Tgraph(CANDLES_DATA, ACTIVE_ORDERS, ORDERBOOK_DATA, SYMBOL)
        self.candles_df = self.cgraph.build_dataframe()

    def test_valid_graph(self):
        self.assertIsInstance(self.cgraph, Tgraph)

    def test_valid_dataframe(self):
        self.assertIsInstance(
            self.candles_df,
            pd.DataFrame
        )

    def test_build_candles_graph(self):
        self.assertIsInstance(
            self.cgraph.build_candles_graph(self.candles_df),
            Figure
        )

    def test_build_rsi_graph(self):
        self.assertIsInstance(
            self.cgraph.build_rsi_graph(self.candles_df),
            Figure
        )

    def test_build_volume_graph(self):
        self.assertIsInstance(
            self.cgraph.build_volume_graph(self.candles_df),
            Figure
        )

    def test_build_active_orders_graph(self):
        self.assertIsInstance(
            self.cgraph.build_active_orders_graph(),
            Figure
        )

    def test_set_colors(self):
        self.assertIsInstance(
            self.cgraph.set_colors(),
            dict
        )

        self.assertIsInstance(
            self.cgraph.set_colors(graphtheme="colorblind"),
            dict
        )

    def test_picture_is_generated(self):
        self.cgraph.save_picture()
        self.assertTrue(
            glob.glob('graph.png')
        )
