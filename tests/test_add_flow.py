from types import SimpleNamespace

from handlers.command_handlers.product_flows import _extract_add_text, _message_thumbnail_file_id


def test_extract_add_text_from_command_args():
    message = SimpleNamespace(text="/add ignored", caption=None)
    command = SimpleNamespace(args="RL 116515LN mete 2022//605.000 HKD")

    assert _extract_add_text(message, command) == "RL 116515LN mete 2022//605.000 HKD"


def test_extract_add_text_strips_caption_command():
    message = SimpleNamespace(text=None, caption="/add Hublot 507.JX.0800.RT.TAK21 full set 2022//120.000 USDT")

    assert _extract_add_text(message) == "Hublot 507.JX.0800.RT.TAK21 full set 2022//120.000 USDT"


def test_extract_add_text_strips_bot_mention_command():
    message = SimpleNamespace(text="/add@jackteamvn_bot RM 07-01RG snow like new 2020//229k USDT", caption=None)

    assert _extract_add_text(message) == "RM 07-01RG snow like new 2020//229k USDT"


def test_message_thumbnail_file_id_uses_largest_photo():
    message = SimpleNamespace(
        photo=[
            SimpleNamespace(file_id="small"),
            SimpleNamespace(file_id="large"),
        ]
    )

    assert _message_thumbnail_file_id(message) == "large"
