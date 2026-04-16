import re


class ProductNormalizer:
    """Conservative normalizer for product text before persistence."""

    VERSION = "v2"

    _PHRASE_PATTERNS = (
        (re.compile(r"\blike\s*new\b", re.IGNORECASE), "like new"),
        (re.compile(r"\bfull[\s\-]*set\b", re.IGNORECASE), "full set"),
        (re.compile(r"\bonly\s*watch\b", re.IGNORECASE), "only watch"),
        (re.compile(r"\bready\s*in\s*hk\b", re.IGNORECASE), "ready in hk"),
    )

    _WORD_MAP = {
        "hkd": "HKD",
        "usdt": "USDT",
        "usd": "USD",
    }
    _CONDITION_WORDS = {"new", "used", "like"}

    @classmethod
    def normalize(cls, text: str) -> str:
        normalized = (text or "").strip()
        if not normalized:
            return ""

        # Normalize spacing and slash separators.
        normalized = re.sub(r"\s*/\s*", "/", normalized)
        normalized = re.sub(r"/{3,}", "//", normalized)
        normalized = re.sub(r"\s{2,}", " ", normalized)

        # Ensure currency suffix attached to number gets a space: 899.000hkd -> 899.000 hkd.
        normalized = re.sub(r"(\d)(hkd|usdt|usd)\b", r"\1 \2", normalized, flags=re.IGNORECASE)

        for pattern, replacement in cls._PHRASE_PATTERNS:
            normalized = pattern.sub(replacement, normalized)
        normalized = re.sub(r"\bfull\s*set(?=\d)", "full set ", normalized, flags=re.IGNORECASE)

        split_tokens = normalized.split(" ")
        tokens = []
        for index, token in enumerate(split_tokens):
            raw = token.strip()
            if not raw:
                continue

            lower = raw.lower()
            next_token = split_tokens[index + 1].strip().lower() if index + 1 < len(split_tokens) else ""

            # Convert thousand separator to comma only in price-like contexts.
            if re.fullmatch(r"\d+\.\d{3}", raw) and next_token in cls._WORD_MAP:
                raw = raw.replace(".", ",")
                lower = raw.lower()

            if lower in cls._WORD_MAP:
                tokens.append(cls._WORD_MAP[lower])
                continue

            if lower in cls._CONDITION_WORDS:
                tokens.append(lower)
                continue

            # Brand shortcut in first token: rl/rm/ap/pp...
            if index == 0 and raw.isalpha() and len(raw) <= 5:
                tokens.append(raw.upper())
                continue

            # Product reference-like token: letters+digits and optional separators.
            if re.fullmatch(r"[a-z0-9][a-z0-9\.\-]*[a-z0-9]", raw, flags=re.IGNORECASE):
                if any(ch.isdigit() for ch in raw) and any(ch.isalpha() for ch in raw):
                    tokens.append(raw.upper())
                    continue

            tokens.append(raw)

        normalized = " ".join(tokens).strip()
        # Normalize shorthand size suffixes.
        normalized = re.sub(r"\b(\d+)\s*K\b", r"\1k", normalized)
        normalized = re.sub(r"\b(\d+(?:\.\d+)?)\s*M\b", r"\1m", normalized)
        return normalized

    @classmethod
    def search_variants(cls, query: str) -> list[str]:
        base = (query or "").strip()
        if not base:
            return []

        normalized = cls.normalize(base)
        variants: list[str] = []
        for value in (base, normalized):
            compact = re.sub(r"\s{2,}", " ", value.strip())
            if compact and compact not in variants:
                variants.append(compact)

        if normalized:
            if "full set" in normalized and "fullset" not in variants:
                variants.append(normalized.replace("full set", "fullset"))
            if "fullset" in normalized and "full set" not in variants:
                variants.append(normalized.replace("fullset", "full set"))

        return variants


normalizer = ProductNormalizer()
