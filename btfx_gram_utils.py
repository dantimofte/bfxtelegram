#!/usr/bin/env python3
"""
Module Docstring
"""

__author__ = "Dan Timofte"
__version__ = "1.0.0"
__license__ = "MIT"


import os
import re
import glob
import json
import pickle

from  datetime import datetime, timedelta
from math import pi
import pandas as pd
#####bokeh libraries
from bokeh.plotting import figure
from bokeh.io import export_png
from bokeh.layouts import layout

def bgu_isnumber(pnumber):
    num_format = re.compile(r"^[\-]?[0-9]*\.?[0-9]*$")
    if re.match(num_format, pnumber):
        return True
    else:
        return False

def bgu_get_date(unixtime):
    time_stamp = unixtime / 1000
    formated_date = datetime.utcfromtimestamp(time_stamp).strftime('%Y-%m-%d %H:%M:%S')
    return formated_date

def bgu_ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def bgu_read_userdata():
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


def bgu_save_userdata(userdata):
    userdata_file = "data/usersdata.pickle"
    bgu_ensure_dir(userdata_file)
    with open(userdata_file, 'wb') as outfile:
        pickle.dump(userdata, outfile)
    human_readable_file = "data/usersdata.json"
    with open(human_readable_file, 'w') as outfile:
        json.dump(userdata, outfile)


def bgu_create_graph(candles_data, active_orders, orders_data, symbol, **kwargs):
    colors_dict = {
        "normal" : ["#98FB98", "#FF0000", "#FF0000", "#98FB98"],
        "colorblind" : ["#00ee00", "#ff00ff", "#ff00ff", "#00ee00"],
        "monochrome" : ["white", "black", "black", "black"]
    }

    up_color = colors_dict['normal'][0]
    down_color = colors_dict['normal'][1]
    sell_order_color = colors_dict['normal'][2]
    buy_order_color = colors_dict['normal'][3]

    for key, value in kwargs.items():
        if key == 'graphtheme':
            up_color = colors_dict[value][0]
            down_color = colors_dict[value][1]
            sell_order_color = colors_dict[value][2]
            buy_order_color = colors_dict[value][3]

    candles_df = pd.DataFrame(
        candles_data,
        columns=['date', 'open', 'close', 'high', 'low', 'volume']
    )

    candles_df['date'] = candles_df['date'].apply(bgu_get_date)
    candles_df['volume'] = candles_df['volume'].astype(int)
    candles_df["date"] = pd.to_datetime(candles_df["date"])
    max_price = candles_df['high'].max()
    min_price = candles_df['low'].min()

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

    inc = candles_df.close > candles_df.open
    dec = candles_df.open > candles_df.close
    candle_width = 30*60*1000 # half an hour in ms

    x_min = candles_df['date'].min() - timedelta(hours=1)
    x_max = candles_df['date'].max() + timedelta(hours=1)
    x_text = candles_df['date'].min()
    candles_graph = figure(
        x_axis_type="datetime",
        toolbar_location=None,
        x_range=(x_min, x_max),
        plot_width=1000,
        title=symbol)
    candles_graph.title.text_font_size = "25pt"
    candles_graph.yaxis.major_label_text_font_size = "15pt"
    candles_graph.yaxis[0].ticker.desired_num_ticks = 20

    candles_graph.xaxis.major_label_text_font_size = "12pt"
    candles_graph.xaxis[0].ticker.desired_num_ticks = 30
    candles_graph.xaxis.major_label_orientation = pi/2
    candles_graph.grid.grid_line_alpha = 0.3


    candles_graph.segment(
        candles_df.date,
        candles_df.high,
        candles_df.date,
        candles_df.low,
        color="black"
    )

    candles_graph.vbar(
        candles_df.date[inc],
        candle_width,
        candles_df.open[inc],
        candles_df.close[inc],
        fill_color=up_color,
        line_color="black"
    )
    candles_graph.vbar(
        candles_df.date[dec],
        candle_width,
        candles_df.open[dec],
        candles_df.close[dec],
        fill_color=down_color,
        line_color="black"
    )

    sells = []
    buys = []
    max_price = float(candles_df['high'].max())
    min_price = float(candles_df['low'].min())
    for order in active_orders:
        price = float(order['price'])
        if price > max_price  or price < min_price:
            continue
        line = [price]*candles_df.shape[0]
        if order['side'] == 'sell':
            sign = "-"
            sells.append(line)
            candles_graph.rect(
                x=x_text+timedelta(hours=3),
                y=price+0.002,
                width=timedelta(hours=7),
                height=0.005,
                fill_color="white"
            )
        else:
            buys.append(line)
            sign = "+"
            candles_graph.rect(
                x=x_text+timedelta(hours=3),
                y=price+0.002,
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

    #### add current price
    current_price = float(candles_df['close'][0])
    new_line = [current_price]*candles_df.shape[0]
    if candles_df['open'][0] > candles_df['close'][0]:
        sells.append(new_line)
        candles_graph.rect(
            x=x_text+timedelta(hours=3),
            y=current_price+0.002,
            width=timedelta(hours=7),
            height=0.005,
            fill_color="white"
        )
    else:
        buys.append(new_line)
        candles_graph.rect(
            x=x_text+timedelta(hours=3),
            y=current_price+0.002,
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

    #add sell lines
    candles_graph.multi_line(
        xs=[candles_df.seq]*len(sells),
        ys=sells,
        line_color=sell_order_color,
        line_dash="dashed",
        line_width=1
    )

    #add buy lines
    candles_graph.multi_line(
        xs=[candles_df.seq]*len(buys),
        ys=buys,
        line_color=buy_order_color,
        line_width=1
    )


    ########### RSI GRAPH

    rsi_graph = figure(
        plot_width=1000,
        plot_height=100,
        x_range=(x_min, x_max),
        toolbar_location=None,
        y_range=(0, 100),
        title="Relative Strength Index"
    )
    rsi_graph.xaxis.visible = False
    rsi_graph.multi_line(
        xs=[candles_df.seq]*4,
        ys=[
            candles_df.rsi_ewma,
            [20]*candles_df.shape[0],
            [50]*candles_df.shape[0],
            [80]*candles_df.shape[0]
        ],
        line_color=['red', 'black', 'gray', 'black'],
        line_width=1
    )
    rsi_graph.yaxis.major_label_text_font_size = "11pt"


    ########### Historic Volume GRAPH
    volume_max = int(candles_df['volume'].max())
    volume_graph = figure(
        plot_width=1000,
        plot_height=100,
        x_range=(x_min, x_max),
        toolbar_location=None,
        y_range=(0, volume_max),
        title="Volume"
    )
    volume_graph.xaxis.visible = False
    volume_graph.left[0].formatter.use_scientific = False

    volume_graph.vbar(
        candles_df.date,
        candle_width,
        candles_df.volume*0,
        candles_df.volume,
        fill_color="blue",
        line_color="black"
    )


    ########### Volume in active orders GRAPH
    orderbook_df = pd.DataFrame.from_dict(orders_data, orient='columns')

    orders_vol_graph = figure(
        plot_width=200,
        toolbar_location=None,
        y_range=orderbook_df.price,
        title="Orderbook"
    )
    orders_vol_graph.below[0].formatter.use_scientific = False
    #orders_vol_grap.left[0].formatter.use_scientific = False
    orders_vol_graph.yaxis.visible = False
    orders_vol_graph.xaxis.major_label_text_font_size = "8pt"
    orders_vol_graph.xaxis[0].ticker.desired_num_ticks = 5
    orders_vol_graph.xaxis.major_label_orientation = pi/2

    orders_vol_graph.hbar(
        y=orderbook_df.price,
        left=orderbook_df.amount*0,
        right=orderbook_df.amount,
        height=0.1
    )

    graphs_layout = layout(
        children=[
            [candles_graph, orders_vol_graph],
            [volume_graph],
            [rsi_graph]
        ]
    )

    ############ export the graph
    export_png(graphs_layout, filename="graph.png")
