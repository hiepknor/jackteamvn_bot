import re


class ListingParser:
    """Deterministic parser for listing CSV title and tags."""

    BRAND_TAG_PATTERNS = (
        ("rolex", (r"\brl\b", r"\brolex\b")),
        ("ap", (r"\bap\b", r"\baudemars\b", r"\bpiguet\b")),
        ("pp", (r"\bpp\b", r"\bpatek\b", r"\bphilippe\b")),
        ("rm", (r"\brm\b", r"\brm(?=\d)", r"\brichard\s+mille\b")),
        ("hublot", (r"\bhublot\b",)),
        ("lange", (r"\ba\.?\s*lange\b", r"\blange\b", r"\bsohne\b")),
        ("zenith", (r"\bzenith\b",)),
        ("omega", (r"\bomega\b",)),
        ("cartier", (r"\bcartier\b",)),
        ("tudor", (r"\btudor\b",)),
        ("vc", (r"\bvc\b", r"\bvacheron\b", r"\bconstantin\b")),
        ("iwc", (r"\biwc\b",)),
        ("panerai", (r"\bpanerai\b", r"\bpam\b")),
    )
    CURRENCY_TAG_PATTERNS = (
        ("hk", r"\b(?:hk|hkd|hong\s*kong)\b"),
        ("usdt", r"(?<![A-Za-z])USDT\b"),
        ("usd", r"(?<![A-Za-z])USD\b"),
    )
    TITLE_STOP_PHRASES = (
        "like new",
        "only watch",
        "ready in hk",
        "full good",
        "full set",
        "new",
        "used",
        "good",
    )

    TITLE_PRICE_PATTERN = re.compile(
        r"(?:\s+|/|-)\d[\d.,]*(?:[kKmM])?\s*(?:HKD|USDT|USD)\b",
        re.IGNORECASE,
    )
    TITLE_STOP_PATTERN = re.compile(
        r"\s+(?:" + "|".join(re.escape(phrase).replace(r"\ ", r"\s+") for phrase in TITLE_STOP_PHRASES) + r")\b",
        re.IGNORECASE,
    )
    TITLE_DATE_PATTERN = re.compile(r"(?:\s+|/|-)(?:\d{1,2}/)?(?:19|20)\d{2}\b")
    REFERENCE_TOKEN_PATTERN = re.compile(r"\b[A-Za-z0-9][A-Za-z0-9./-]*[A-Za-z0-9]\b")

    @staticmethod
    def compact(value: str | None) -> str:
        return re.sub(r"\s+", " ", (value or "").strip())

    @classmethod
    def title_from_text(cls, text: str | None, fallback: str) -> str:
        title = cls.compact(text)
        if not title:
            return fallback

        title = re.split(r"\s*//\s*", title, maxsplit=1)[0].strip()
        for pattern in (cls.TITLE_PRICE_PATTERN, cls.TITLE_STOP_PATTERN, cls.TITLE_DATE_PATTERN):
            match = pattern.search(title)
            if match:
                title = title[: match.start()].strip()

        title = re.sub(r"[\s/\-]+$", "", title).strip()
        title = cls.normalize_reference_case(title)

        return title or fallback

    @classmethod
    def tags_from_text(cls, text: str | None) -> str:
        value = cls.compact(text)
        if not value:
            return ""

        tags: list[str] = []
        for tag, patterns in cls.BRAND_TAG_PATTERNS:
            if any(re.search(pattern, value, re.IGNORECASE) for pattern in patterns):
                tags.append(tag)

        for tag, pattern in cls.CURRENCY_TAG_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                tags.append(tag)

        return ",".join(tags)

    @classmethod
    def normalize_reference_case(cls, title: str) -> str:
        def normalize_token(match: re.Match[str]) -> str:
            token = match.group(0)
            if any(ch.isalpha() for ch in token) and any(ch.isdigit() for ch in token):
                return token.upper()
            return token

        return cls.REFERENCE_TOKEN_PATTERN.sub(normalize_token, title)


listing_parser = ListingParser()
