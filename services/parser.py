import re
from typing import Dict, Any, List, Tuple
from utils.logger import logger


class ProductParser:
    """Parser for Jack Stock Bot product lines"""
    
    # Known watch brands
    KNOWN_BRANDS = {
        "RL", "PP", "AP", "OM", "TU", "CA", "SE", "RO", "PA", "AU",
        "ROLEX", "PATEK", "AUDEMARS", "OMEGA", "TUDOR", "CARTIER",
        "SEIKO", "PANERAI", "AUDEMARSPIGUET"
    }
    
    @staticmethod
    def normalize_line(line: str) -> str:
        line = line.strip()
        line = re.sub(r"[|]+", " ", line)
        line = re.sub(r"[/]{2,}", " ", line)
        line = re.sub(r"\s+", " ", line)
        return line
    
    @staticmethod
    def parse(line: str) -> Dict[str, Any]:
        raw_original = line.strip()
        parsed_text = ProductParser.normalize_line(line)
        
        result = {
            "raw_text": raw_original,
            "brand": None,
            "model": None,
            "dial_desc": None,
            "condition": None,
            "date_info": None,
            "price_text": None,
            "currency": None,
            "note": None,
            "parse_confidence": 0.0,
        }
        
        tokens = parsed_text.split()
        if not tokens:
            return result
        
        # Brand detection
        first_token = tokens[0].upper()
        if first_token in ProductParser.KNOWN_BRANDS or len(first_token) <= 4:
            result["brand"] = first_token
            result["parse_confidence"] += 0.2
        
        # Model detection
        if len(tokens) >= 2:
            potential_model = tokens[1].upper()
            if re.match(r"^\d+[A-Z]*[A-Z0-9]*$", potential_model):
                result["model"] = potential_model
                result["parse_confidence"] += 0.2
        
        # Currency detection
        currency_match = re.search(r"\b(HKD|USDT|USD|EUR|VND|CNY)\b", parsed_text, re.IGNORECASE)
        if currency_match:
            result["currency"] = currency_match.group(1).upper()
            result["parse_confidence"] += 0.15
        
        # Condition detection
        condition_match = re.search(r"\b(new|used|mint|excellent|good|fair|like|box|paper)\b", 
                                    parsed_text, re.IGNORECASE)
        if condition_match:
            result["condition"] = condition_match.group(1).lower()
            result["parse_confidence"] += 0.15
        
        # Date detection
        date_match = re.search(r"\b(\d{1,2}/\d{4}|\d{4})\b", parsed_text)
        if date_match:
            result["date_info"] = date_match.group(1)
            result["parse_confidence"] += 0.1
        
        # Price detection
        price_match = re.search(
            r"\b(\d+(?:[.,]\d+)?m|\d+(?:[.,]\d+)?k|\d[\d.,]*)\b",
            parsed_text, re.IGNORECASE
        )
        if price_match:
            result["price_text"] = price_match.group(1)
            result["parse_confidence"] += 0.2
        
        # Description extraction
        desc_start = 2
        stop_indexes: List[int] = []
        
        for i, token in enumerate(tokens):
            token_lower = token.lower()
            if token_lower in {"new", "used", "mint", "hkd", "usdt", "usd", "eur", "vnd", "cny"}:
                stop_indexes.append(i)
            elif re.fullmatch(r"\d{1,2}/\d{4}|\d{4}", token):
                stop_indexes.append(i)
            elif re.fullmatch(r"\d+(?:[.,]\d+)?m|\d+(?:[.,]\d+)?k|\d[\d.,]*", token_lower):
                stop_indexes.append(i)
        
        valid_stops = [i for i in stop_indexes if i >= desc_start]
        first_stop = min(valid_stops) if valid_stops else len(tokens)
        
        if first_stop > desc_start:
            result["dial_desc"] = " ".join(tokens[desc_start:first_stop])
            result["parse_confidence"] += 0.1
        
        # Note extraction
        if currency_match:
            end_pos = currency_match.end()
            note = parsed_text[end_pos:].strip(" /-")
            if note:
                result["note"] = note
        
        result["parse_confidence"] = min(result["parse_confidence"], 1.0)
        logger.debug(f"Parsed line with confidence: {result['parse_confidence']:.2f}")
        
        return result
    
    @staticmethod
    def validate_parsed_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        warnings = []
        
        if not data.get("brand"):
            warnings.append("⚠️ Không phát hiện thương hiệu")
        
        if not data.get("model"):
            warnings.append("⚠️ Không phát hiện model")
        
        if not data.get("price_text"):
            warnings.append("⚠️ Không phát hiện giá")
        
        if not data.get("currency"):
            warnings.append("⚠️ Không phát hiện đơn vị tiền tệ")
        
        if data.get("parse_confidence", 0) < 0.5:
            warnings.append("⚠️ Độ chính xác phân tích thấp (< 50%)")
        
        return len(warnings) == 0, warnings


product_parser = ProductParser()
