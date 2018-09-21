#!/usr/bin/env python3
"""
docstring
"""

from datetime import datetime, timedelta
from math import pi
import pandas as pd

# bokeh libraries
from bokeh.plotting import figure
from bokeh.io import export_png
from bokeh.layouts import layout


COLOR_THEME = {
    "normal":
    {"up": "#98FB98", "down": "#FF0000", "sell_order": "#FF0000", "buy_order": "#98FB98"},
    "colorblind":
    {"up": "#00ee00", "down": "#ff00ff", "sell_order": "#ff00ff", "buy_order": "#00ee00"},
    "monochrome":
    {"up": "white", "down": "black", "sell_order": "black", "buy_order": "black"}
}


class Tgraph:
    def __init__(self, candles_data, active_orders, orders_data, symbol, **kwargs):
        self.colors = self.set_colors(**kwargs)
        self.symbol = symbol
        self.candles_data = candles_data
        self.active_orders = active_orders
        self.orders_data = orders_data

        candles_df = self.build_dataframe()

        self.candle_width = 30 * 60 * 1000  # half an hour in ms

        self.x_min = candles_df['date'].min() - timedelta(hours=1)
        self.x_max = candles_df['date'].max() + timedelta(hours=1)

        cdl_graph = self.build_candles_graph(candles_df)
        ao_graph = self.build_active_orders_graph()
        vol_graph = self.build_volume_graph(candles_df)
        rsi_graph = self.build_rsi_graph(candles_df)

        self.graphs_layout = layout(
            children=[
                [cdl_graph, ao_graph],
                [vol_graph],
                [rsi_graph]
            ]
        )

    def build_dataframe(self):
        candles_df = pd.DataFrame(
            self.candles_data,
            columns=['date', 'open', 'close', 'high', 'low', 'volume']
        )

        def get_date(unixtime):
            time_stamp = unixtime / 1000
            formated_date = datetime.utcfromtimestamp(time_stamp).strftime('%Y-%m-%d %H:%M:%S')
            return formated_date

        candles_df['date'] = candles_df['date'].apply(get_date)
        candles_df['volume'] = candles_df['volume'].astype(int)
        candles_df["date"] = pd.to_datetime(candles_df["date"])

        # Window length for moving average
        window_length = 14
        candles_df['seq'] = candles_df['date']
        close = candles_df['close'][::-1]
        # Get the difference in price from previous step
        delta = close.diff()
        # Make the positive gains (up) and negative gains (down) Series
        up_gains, down_gains = delta.copy(), delta.copy()
        up_gains[up_gains < 0] = 0
        down_gains[down_gains > 0] = 0
        # Calculate the EWMA
        roll_up1 = up_gains.ewm(
            com=window_length,
            min_periods=0,
            adjust=True,
            ignore_na=False
        ).mean()

        roll_down1 = down_gains.abs().ewm(
            com=window_length,
            min_periods=0,
            adjust=True,
            ignore_na=False
        ).mean()

        # Calculate the RSI based on EWMA
        rs1 = roll_up1 / roll_down1
        rsi1 = 100.0 - (100.0 / (1.0 + rs1))
        candles_df['rsi_ewma'] = rsi1
        candles_df = candles_df[::-1][16:]

        return candles_df

    def build_candles_graph(self, candles_df):
        x_text = candles_df['date'].min()

        candles_graph = figure(
            x_axis_type="datetime",
            toolbar_location=None,
            x_range=(self.x_min, self.x_max),
            plot_width=1000,
            title=self.symbol)
        candles_graph.title.text_font_size = "25pt"
        candles_graph.yaxis.major_label_text_font_size = "15pt"
        candles_graph.yaxis[0].ticker.desired_num_ticks = 20

        candles_graph.xaxis.major_label_text_font_size = "12pt"
        candles_graph.xaxis[0].ticker.desired_num_ticks = 30
        candles_graph.xaxis.major_label_orientation = pi / 2
        candles_graph.grid.grid_line_alpha = 0.3

        candles_graph.segment(
            candles_df.date,
            candles_df.high,
            candles_df.date,
            candles_df.low,
            color="black"
        )

        inc = candles_df.close > candles_df.open
        candles_graph.vbar(
            candles_df.date[inc],
            self.candle_width,
            candles_df.open[inc],
            candles_df.close[inc],
            fill_color=self.colors['up'],
            line_color="black"
        )
        dec = candles_df.open > candles_df.close
        candles_graph.vbar(
            candles_df.date[dec],
            self.candle_width,
            candles_df.open[dec],
            candles_df.close[dec],
            fill_color=self.colors['down'],
            line_color="black"
        )

        sells = []
        buys = []
        max_price = float(candles_df['high'].max())
        min_price = float(candles_df['low'].min())
        for order in self.active_orders:
            price = float(order['price'])
            if price > max_price or price < min_price:
                continue
            line = [price] * candles_df.shape[0]
            if order['side'] == 'sell':
                sign = "-"
                sells.append(line)
                candles_graph.rect(
                    x=x_text + timedelta(hours=3),
                    y=price + 0.002,
                    width=timedelta(hours=7),
                    height=0.005,
                    fill_color="white"
                )
            else:
                buys.append(line)
                sign = "+"
                candles_graph.rect(
                    x=x_text + timedelta(hours=3),
                    y=price + 0.002,
                    width=timedelta(hours=7),
                    height=0.005,
                    fill_color="white"
                )
            candles_graph.text(
                x=x_text,
                y=price,
                text=[f"{sign}{order['remaining_amount']}"],
                text_font_size='8pt',
                text_font_style='bold'
            )

        # add current price
        current_price = float(candles_df['close'][0])
        new_line = [current_price] * candles_df.shape[0]
        if candles_df['open'][0] > candles_df['close'][0]:
            sells.append(new_line)
            candles_graph.rect(
                x=x_text + timedelta(hours=3),
                y=current_price + 0.002,
                width=timedelta(hours=7),
                height=0.005,
                fill_color="white"
            )
        else:
            buys.append(new_line)
            candles_graph.rect(
                x=x_text + timedelta(hours=3),
                y=current_price + 0.002,
                width=timedelta(hours=7),
                height=0.005,
                fill_color="white"
            )

        candles_graph.text(
            x=x_text,
            y=current_price,
            text=[f"{current_price}"],
            text_font_size='8pt',
            text_font_style='bold'
        )

        # add sell lines
        candles_graph.multi_line(
            xs=[candles_df.seq] * len(sells),
            ys=sells,
            line_color=self.colors['sell_order'],
            line_dash="dashed",
            line_width=1
        )

        # add buy lines
        candles_graph.multi_line(
            xs=[candles_df.seq] * len(buys),
            ys=buys,
            line_color=self.colors['buy_order'],
            line_width=1
        )
        return candles_graph

    def build_rsi_graph(self, candles_df):
        rsi_graph = figure(
            plot_width=1000,
            plot_height=100,
            x_range=(self.x_min, self.x_max),
            toolbar_location=None,
            y_range=(0, 100),
            title="Relative Strength Index"
        )
        rsi_graph.xaxis.visible = False
        rsi_graph.multi_line(
            xs=[candles_df.seq] * 4,
            ys=[
                candles_df.rsi_ewma,
                [20] * candles_df.shape[0],
                [50] * candles_df.shape[0],
                [80] * candles_df.shape[0]
            ],
            line_color=['red', 'black', 'gray', 'black'],
            line_width=1
        )
        rsi_graph.yaxis.major_label_text_font_size = "11pt"

        return rsi_graph

    def build_volume_graph(self, candles_df):
        # Historic Volume GRAPH
        volume_max = int(candles_df['volume'].max())
        volume_graph = figure(
            plot_width=1000,
            plot_height=100,
            x_range=(self.x_min, self.x_max),
            toolbar_location=None,
            y_range=(0, volume_max),
            title="Volume"
        )
        volume_graph.xaxis.visible = False
        volume_graph.left[0].formatter.use_scientific = False

        volume_graph.vbar(
            candles_df.date,
            self.candle_width,
            candles_df.volume * 0,
            candles_df.volume,
            fill_color="blue",
            line_color="black"
        )
        return volume_graph

    def build_active_orders_graph(self):
        # Volume in active orders GRAPH
        orderbook_df = pd.DataFrame.from_dict(self.orders_data, orient='columns')

        orders_vol_graph = figure(
            plot_width=200,
            toolbar_location=None,
            y_range=orderbook_df.price,
            title="Orderbook"
        )
        orders_vol_graph.below[0].formatter.use_scientific = False
        orders_vol_graph.yaxis.visible = False
        orders_vol_graph.xaxis.major_label_text_font_size = "8pt"
        orders_vol_graph.xaxis[0].ticker.desired_num_ticks = 5
        orders_vol_graph.xaxis.major_label_orientation = pi / 2

        orders_vol_graph.hbar(
            y=orderbook_df.price,
            left=orderbook_df.amount * 0,
            right=orderbook_df.amount,
            height=0.1
        )

        return orders_vol_graph

    def set_colors(self, **kwargs):
        colors_dict = {}
        colors_dict['up'] = COLOR_THEME['normal']['up']
        colors_dict['down'] = COLOR_THEME['normal']['down']
        colors_dict['sell_order'] = COLOR_THEME['normal']['sell_order']
        colors_dict['buy_order'] = COLOR_THEME['normal']['buy_order']
        for key, value in kwargs.items():
            if key == 'graphtheme':
                colors_dict['up'] = COLOR_THEME[value]['up']
                colors_dict['down'] = COLOR_THEME[value]['down']
                colors_dict['sell_order'] = COLOR_THEME[value]['sell_order']
                colors_dict['buy_order'] = COLOR_THEME[value]['buy_order']
        return colors_dict

    def save_picture(self):
        # export the graph
        export_png(self.graphs_layout, filename="graph.png")
