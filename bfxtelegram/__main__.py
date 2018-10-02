#!/usr/bin/env python3
"""
Module Docstring
"""

__author__ = "Dan Timofte"
__version__ = "1.0.0"
__license__ = "MIT"

import os
from bfxtelegram.btfxbot import Btfxbot


def main():
    Btfxbot(
        os.environ.get('TELEGRAM_TOKEN'),
        os.environ.get('AUTH_PASS'),
        os.environ.get('BFX_TELEGRAM_KEY'),
        os.environ.get('BFX_TELEGRAM_SECRET')
    )


if __name__ == "__main__":
    main()
