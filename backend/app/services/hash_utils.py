import hashlib
import json
from typing import Any


def sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def sha256_json(data: Any) -> str:
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(encoded)


def request_hash(data: dict[str, Any]) -> str:
    return sha256_json(data)
