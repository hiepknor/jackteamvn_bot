import pytest

from services.listing_parser import listing_parser


LISTING_CASES = [
    ("Hublot 682.SX.9800.LR.0999//12/2024//260.000 HKD", "Hublot 682.SX.9800.LR.0999", "hublot,hk"),
    ("Hublot 507.JX.0800.RT.TAK21 full set 2022//120.000 USDT", "Hublot 507.JX.0800.RT.TAK21", "hublot,usdt"),
    (
        "Hublot MP-17 MECA-10 ARSHAM SPLASH titanium sapphire new 2025//55k USDT",
        "Hublot MP-17 MECA-10 ARSHAM SPLASH titanium sapphire",
        "hublot,usdt",
    ),
    ("A.lange&sohne 182.886 new full set 12/2024//390.000 HKD", "A.lange&sohne 182.886", "lange,hk"),
    (
        "Zenith Defy 03.A780.400-3/56.M3642 Limited Edition//10/2025//11,000 USDT",
        "Zenith Defy 03.A780.400-3/56.M3642 Limited Edition",
        "zenith,usdt",
    ),
    ("RL 116515LN mete 2022//605.000 HKD", "RL 116515LN mete", "rolex,hk"),
    ("RL 278288RBR used 2020 340k HKD only watch", "RL 278288RBR", "rolex,hk"),
    ("AP 26240OR black full good full set 2023//105k USDT", "AP 26240OR black", "ap,usdt"),
    ("AP 67651ST white 2019//40k USDT", "AP 67651ST white", "ap,usdt"),
    ("AP 67651ST white 2024//46k USDT", "AP 67651ST white", "ap,usdt"),
    ("AP 26540or/2016/899.000 HKD", "AP 26540OR", "ap,hk"),
    ("AP 77350CB new 2024//69k USDT", "AP 77350CB", "ap,usdt"),
    ("AP 67651SR new 2026//53k USDT ready in hk", "AP 67651SR", "ap,hk,usdt"),
    ("AP 67651SR like new 2024//48k USDT", "AP 67651SR", "ap,usdt"),
    ("PP 5271/12P-010 new full set 4/2025//545.000 USDT", "PP 5271/12P-010", "pp,usdt"),
    ("PP 7041R-001 like new 11/2018//179.000 HKD", "PP 7041R-001", "pp,hk"),
    ("RM 037 WHITE CERAMIC new 3//2026//275k USDT", "RM 037 WHITE CERAMIC", "rm,usdt"),
    ("RM07-01 black ceramic black lips 2023//225k USDT", "RM07-01 black ceramic black lips", "rm,usdt"),
    ("AP 15450SR full set 2021 - 310,000 HKD", "AP 15450SR", "ap,hk"),
    ("RM 07-01RG snow like new 2020//229k USDT", "RM 07-01RG snow", "rm,usdt"),
    ("PP 7118/1A grey like new 2022 - 560,000 HKD", "PP 7118/1A grey", "pp,hk"),
]


@pytest.mark.parametrize(("text", "expected_title", "expected_tags"), LISTING_CASES)
def test_listing_parser_extracts_title_and_tags(text, expected_title, expected_tags):
    assert listing_parser.title_from_text(text, "Item 1") == expected_title
    assert listing_parser.tags_from_text(text) == expected_tags


def test_listing_parser_title_fallback_for_empty_text():
    assert listing_parser.title_from_text("", "Item 1") == "Item 1"
