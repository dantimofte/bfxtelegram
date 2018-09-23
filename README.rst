# bfxtelegram
Control your bitfinex account using a telegram bot

## Set-up

	get a telegram bot token from `botfather <https://t.me/BotFather>`_
	get api key and secret from bitfinex
	set all the environment variables from the .env-example

	List of public commands for BotFather:
	start - /start : Initiate chat and check if the bot is running
	auth - /auth you_bot_password 
	orders - /orders (list of active orders)
	neworder - /neworder ±volume price tradepair tradetype
	graph - /graph symbol (symbol is optional, default is iotusd)
	set - /set option value 
	calc - /calc "calculation"
	help - /help "command"

## Documentation
	Please check the `wiki <https://github.com/dantimofte/bfxtelegram/wiki>`_
