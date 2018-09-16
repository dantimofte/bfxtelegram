#W0613:Unused argument
#C0103:Method name too long
# pylint: disable=W0613,C0103

import glob
from bfxtelegram import utils

def test_isnumber():
    assert utils.isnumber("100.4")
    assert not utils.isnumber("100.a")

def test_get_date():
    assert utils.get_date(1537092000000) == '2018-09-16 10:00:00'

def test_ensure_dir():
    assert utils.ensure_dir("tests/__pycache__") is None

def test_read_userdata():
    userdata = utils.read_userdata()
    assert isinstance(userdata, dict)

def test_save_userdata():
    userdata = utils.read_userdata()
    assert utils.save_userdata(userdata) is None
    assert glob.glob('data/usersdata.pickle')
    assert glob.glob('data/usersdata.json')
