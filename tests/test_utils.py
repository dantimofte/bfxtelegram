from bfxtelegram import utils



def test_send_message():
    assert utils.isnumber("100.4")
    assert not utils.isnumber("100.4a")


def test_isnumber():
    assert utils.isnumber("100.4")
    assert not utils.isnumber("100.4a")
