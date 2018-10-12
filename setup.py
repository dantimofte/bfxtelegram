from setuptools import setup, find_packages

VERSION = '1.0.2'

# Runtime dependencies. See requirements.txt for development dependencies.
DEPENDENCIES = [
    "wheel",
    "pandas",
    "pillow",
    "selenium",
    "bokeh",
    "python-telegram-bot",
    "bitfinex-v2==1.0.0"
]

setup(
    name='bfxtelegram',
    version=VERSION,
    description='Control Bitfinex account with a Telegram bot',
    author='Dan Timofte',
    author_email='dantimofte@pm.me',
    url='https://github.com/dantimofte/bfxtelegram',
    license='MIT',
    packages=find_packages(),
    install_requires=DEPENDENCIES,
    keywords=['bitcoin', 'btc', 'iota', 'telegram', 'bitfinex'],
    classifiers=[],
    zip_safe=True,
    entry_points={
        "console_scripts": [
            "bfxtelegram = bfxtelegram.__main__:main",
        ],
    },

)
