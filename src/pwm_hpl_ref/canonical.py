import hashlib, json
from typing import Any

def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha256_urn(namespace: str, value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value)).hexdigest()
    return f"urn:{namespace}:sha256:{digest}"
