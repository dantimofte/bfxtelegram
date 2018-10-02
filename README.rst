============
bfxtelegram
============

Control your bitfinex account using a telegram bot

======
Set-up
======

get a telegram bot token from `botfather <https://t.me/BotFather>`_

get api key and secret from `bitfinex <https://www.bitfinex.com/>`_

set all the environment variables from the `.env-example <https://github.com/dantimofte/bfxtelegram/blob/master/.env-example>`_

List of public commands for BotFather:
:: 

  start - /start : Initiate chat and check if the bot is running
  auth - /auth you_bot_password 
  graph - /graph symbol (symbol is optional, default is iotusd)
  orders - /orders (list of active orders)
  neworder - /neworder ±volume price tradepair tradetype
  newalert - /newalert tradepair price
  set - /set option value
  getbalance - /getbalance
  enable - /enable message_type
  disable - /disable message_type
  calc - /calc "calculation"
  help - /help "command"

=============
Demo
=============

.. image:: https://i.imgur.com/CbZTEtl.png

.. image:: https://i.imgur.com/ZK9vl7w.png

.. image:: https://i.imgur.com/SNNcR0p.png

.. image:: https://i.imgur.com/Pv5slp4.png


=============
Documentation
=============
Please check the `wiki <https://github.com/dantimofte/bfxtelegram/wiki>`_

