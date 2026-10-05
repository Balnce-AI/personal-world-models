#!/usr/bin/env python3
"""Independent verifier for the PWM public provenance profile vectors."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

EVENT_BODY_DOMAIN = b"pwm:event-body:v1\0"
PAYLOAD_DOMAIN = b"pwm:payload:v1\0"
RECEIPT_BODY_DOMAIN = b"pwm:append-receipt-body:v1\0"
KEY_FRONTIER_DOMAIN = b"pwm:key-status-frontier:v1\0"
EVENT_SIGNATURE_DOMAIN = b"pwm:event-signature:v1\0"
RECEIPT_SIGNATURE_DOMAIN = b"pwm:append-receipt-signature:v1\0"
CID_PREFIX = bytes.fromhex("01551220")


class ProfileError(ValueError):
    pass


@dataclass
class Decoder:
    data: bytes
    offset: int = 0
    items: int = 0

    def decode(self, depth: int = 0) -> Any:
        if depth > 64 or self.offset >= len(self.data):
            raise ProfileError("resource limit or truncated input")
        self.items += 1
        if self.items > 1_000_000:
            raise ProfileError("item limit")
        initial = self._byte()
        major, additional = initial >> 5, initial & 31
        if major in (0, 1):
            value = self._argument(additional)
            if major == 0:
                return value
            if value > 2**63 - 1:
                raise ProfileError("negative integer below i64 minimum")
            return -1 - value
        if major in (2, 3):
            length = self._argument(additional)
            if length > 16 * 1024 * 1024 or self.offset + length > len(self.data):
                raise ProfileError("byte/text limit or truncation")
            raw = self.data[self.offset : self.offset + length]
            self.offset += length
            if major == 2:
                return raw
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as error:
                raise ProfileError("invalid UTF-8") from error
            if unicodedata.normalize("NFC", text) != text:
                raise ProfileError("non-NFC text")
            return text
        if major == 4:
            length = self._argument(additional)
            return [self.decode(depth + 1) for _ in range(length)]
        if major == 5:
            length = self._argument(additional)
            result: dict[str, Any] = {}
            previous_key_bytes: bytes | None = None
            for _ in range(length):
                key_start = self.offset
                key = self.decode(depth + 1)
                key_bytes = self.data[key_start : self.offset]
                if not isinstance(key, str):
                    raise ProfileError("map key is not text")
                if previous_key_bytes is not None and key_bytes <= previous_key_bytes:
                    raise ProfileError("duplicate or unsorted map key")
                previous_key_bytes = key_bytes
                result[key] = self.decode(depth + 1)
            return result
        if major == 7 and additional in (20, 21, 22):
            return {20: False, 21: True, 22: None}[additional]
        raise ProfileError("unsupported CBOR type")

    def _byte(self) -> int:
        if self.offset >= len(self.data):
            raise ProfileError("truncated input")
        value = self.data[self.offset]
        self.offset += 1
        return value

    def _argument(self, additional: int) -> int:
        if additional < 24:
            return additional
        sizes = {24: 1, 25: 2, 26: 4, 27: 8}
        size = sizes.get(additional)
        if size is None or self.offset + size > len(self.data):
            raise ProfileError("indefinite or truncated argument")
        raw = self.data[self.offset : self.offset + size]
        self.offset += size
        value = int.from_bytes(raw, "big")
        minima = {1: 24, 2: 256, 4: 65_536, 8: 2**32}
        if value < minima[size]:
            raise ProfileError("non-shortest argument")
        return value


def decode_canonical(data: bytes) -> Any:
    decoder = Decoder(data)
    value = decoder.decode()
    if decoder.offset != len(data) or encode(value) != data:
        raise ProfileError("trailing or non-canonical data")
    return value


def encode(value: Any) -> bytes:
    if value is None:
        return b"\xf6"
    if value is False:
        return b"\xf4"
    if value is True:
        return b"\xf5"
    if isinstance(value, int):
        if value >= 0:
            if value > 2**64 - 1:
                raise ProfileError("unsigned integer overflow")
            return argument(0, value)
        if value < -(2**63):
            raise ProfileError("negative integer overflow")
        return argument(1, -1 - value)
    if isinstance(value, bytes):
        return argument(2, len(value)) + value
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise ProfileError("non-NFC text")
        raw = value.encode("utf-8")
        return argument(3, len(raw)) + raw
    if isinstance(value, list):
        return argument(4, len(value)) + b"".join(encode(item) for item in value)
    if isinstance(value, dict):
        entries = sorted(((encode(key), encode(item)) for key, item in value.items()), key=lambda pair: pair[0])
        if any(not isinstance(key, str) for key in value):
            raise ProfileError("map key is not text")
        return argument(5, len(entries)) + b"".join(key + item for key, item in entries)
    raise ProfileError("unsupported value")


def argument(major: int, value: int) -> bytes:
    prefix = major << 5
    if value < 24:
        return bytes([prefix | value])
    for additional, size, maximum in ((24, 1, 0xFF), (25, 2, 0xFFFF), (26, 4, 0xFFFFFFFF), (27, 8, 0xFFFFFFFFFFFFFFFF)):
        if value <= maximum:
            return bytes([prefix | additional]) + value.to_bytes(size, "big")
    raise ProfileError("argument overflow")


def cid(domain: bytes, canonical_bytes: bytes) -> bytes:
    return CID_PREFIX + hashlib.sha256(domain + canonical_bytes).digest()


def cid_text(raw: bytes) -> str:
    return "b" + base64.b32encode(raw).decode("ascii").lower().rstrip("=")


def verify_signature(public_key: bytes, domain: bytes, cid_bytes: bytes, signature: bytes) -> None:
    if len(cid_bytes) != 36 or not cid_bytes.startswith(CID_PREFIX):
        raise ProfileError("invalid CID profile")
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, domain + cid_bytes[2:])
    except InvalidSignature as error:
        raise ProfileError("signature invalid") from error


def require_exact_fields(value: Any, fields: set[str], record_name: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise ProfileError(f"invalid {record_name} fields")
    return value


def require_text(value: Any, field: str) -> str:
    if type(value) is not str:
        raise ProfileError(f"{field} must be text")
    return value


def require_unsigned(value: Any, field: str) -> int:
    if type(value) is not int or not 0 <= value <= 2**64 - 1:
        raise ProfileError(f"{field} must be an unsigned 64-bit integer")
    return value


def require_integer(value: Any, field: str) -> int:
    if type(value) is not int or not -(2**63) <= value <= 2**63 - 1:
        raise ProfileError(f"{field} must be a signed 64-bit integer")
    return value


def require_cid(value: Any, field: str) -> bytes:
    if type(value) is not bytes or len(value) != 36 or not value.startswith(CID_PREFIX):
        raise ProfileError(f"{field} must be a profile CID")
    return value


def validate_event_body(value: Any) -> dict[str, Any]:
    body = require_exact_fields(
        value,
        {
            "schema_version",
            "event_kind",
            "author_key_id",
            "principal_scope",
            "parent_event_cids",
            "author_sequence",
            "event_time",
            "payload_cid",
        },
        "EventBody",
    )
    for field in ("schema_version", "event_kind", "author_key_id", "principal_scope"):
        require_text(body[field], field)
    require_unsigned(body["author_sequence"], "author_sequence")
    require_integer(body["event_time"], "event_time")
    require_cid(body["payload_cid"], "payload_cid")
    if type(body["parent_event_cids"]) is not list:
        raise ProfileError("parent_event_cids must be an array")
    for parent in body["parent_event_cids"]:
        require_cid(parent, "parent_event_cids item")
    return body


def validate_receipt_body(value: Any) -> dict[str, Any]:
    receipt = require_exact_fields(
        value,
        {
            "body_cid",
            "ingestion_time",
            "key_status_frontier_cid",
            "log_sequence",
            "appender_key_id",
        },
        "AppendReceiptBody",
    )
    require_cid(receipt["body_cid"], "body_cid")
    require_integer(receipt["ingestion_time"], "ingestion_time")
    require_cid(receipt["key_status_frontier_cid"], "key_status_frontier_cid")
    require_unsigned(receipt["log_sequence"], "log_sequence")
    require_text(receipt["appender_key_id"], "appender_key_id")
    return receipt


def _verify_bundle_data(bundle: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    if bundle.get("profile") != "pwm-public-provenance-v1":
        raise ProfileError("unsupported profile")
    appender = bytes.fromhex(bundle["appender_public_key_hex"])
    key_state: dict[str, dict[str, Any]] = {}
    key_frontiers: dict[bytes, dict[str, dict[str, Any]]] = {}

    def capture_frontier() -> None:
        encoded_state = [
            {
                "key_id": key_id,
                "public_key": record["public_key"],
                "active_from_log_sequence": record["active_from_log_sequence"],
                "revoked_at_log_sequence": record["revoked_at_log_sequence"],
            }
            for key_id, record in sorted(key_state.items())
        ]
        frontier = cid(KEY_FRONTIER_DOMAIN, encode(encoded_state))
        key_frontiers[frontier] = {key_id: record.copy() for key_id, record in key_state.items()}

    for item in bundle["author_keys"]:
        key_id = item["key_id"]
        if key_id in key_state:
            raise ProfileError("duplicate key ID")
        key_state[key_id] = {
            "public_key": bytes.fromhex(item["public_key_hex"]),
            "active_from_log_sequence": item["active_from_log_sequence"],
            "revoked_at_log_sequence": None,
        }
        capture_frontier()
    for item in bundle["author_keys"]:
        revoked = item["revoked_at_log_sequence"]
        if revoked is not None:
            if revoked < key_state[item["key_id"]]["active_from_log_sequence"]:
                raise ProfileError("invalid key transition")
            key_state[item["key_id"]]["revoked_at_log_sequence"] = revoked
            capture_frontier()
    schemas = {item["event_kind"]: item["schema_version"] for item in bundle["schemas"]}
    events: dict[bytes, dict[str, Any]] = {}
    verified_records: dict[bytes, dict[str, Any]] = {}
    sequence_index: set[tuple[str, str, int]] = set()

    for expected_log_sequence, record in enumerate(bundle["records"]):
        body_bytes = bytes.fromhex(record["body_cbor_hex"])
        body = validate_event_body(decode_canonical(body_bytes))
        body_cid = cid(EVENT_BODY_DOMAIN, body_bytes)
        if cid_text(body_cid) != record["body_cid"]:
            raise ProfileError("event CID mismatch")
        payload = bytes.fromhex(record["payload_cbor_hex"])
        decode_canonical(payload)
        if body["payload_cid"] != cid(PAYLOAD_DOMAIN, payload):
            raise ProfileError("payload CID mismatch")
        if schemas.get(body["event_kind"]) != body["schema_version"]:
            raise ProfileError("schema mismatch")

        receipt_bytes = bytes.fromhex(record["receipt_body_cbor_hex"])
        receipt = validate_receipt_body(decode_canonical(receipt_bytes))
        receipt_cid = cid(RECEIPT_BODY_DOMAIN, receipt_bytes)
        if cid_text(receipt_cid) != record["receipt_cid"]:
            raise ProfileError("receipt CID mismatch")
        frontier = receipt["key_status_frontier_cid"]
        frontier_state = key_frontiers.get(frontier)
        if frontier_state is None:
            raise ProfileError("unknown key-status frontier")
        key_record = frontier_state.get(body["author_key_id"])
        if key_record is None or expected_log_sequence < key_record["active_from_log_sequence"]:
            raise ProfileError("key is not active")
        revoked = key_record["revoked_at_log_sequence"]
        if revoked is not None and expected_log_sequence >= revoked:
            raise ProfileError("key is revoked")
        verify_signature(key_record["public_key"], EVENT_SIGNATURE_DOMAIN, body_cid, bytes.fromhex(record["event_signature_hex"]))
        parents = body["parent_event_cids"]
        if parents != sorted(parents) or len(parents) != len(set(parents)):
            raise ProfileError("parents not sorted and unique")
        if body["event_kind"] == "pwm.genesis":
            if parents or body["author_sequence"] != 0 or any(event["principal_scope"] == body["principal_scope"] for event in events.values()):
                raise ProfileError("invalid genesis")
        elif not parents:
            raise ProfileError("non-genesis has no parent")
        for parent in parents:
            if parent not in events or events[parent]["principal_scope"] != body["principal_scope"]:
                raise ProfileError("missing or cross-scope parent")
        sequence_key = (body["principal_scope"], body["author_key_id"], body["author_sequence"])
        if sequence_key in sequence_index:
            raise ProfileError("duplicate author sequence")
        if body["author_sequence"] > 0:
            predecessor = (body["principal_scope"], body["author_key_id"], body["author_sequence"] - 1)
            if predecessor not in sequence_index or not ancestor_contains(events, parents, predecessor):
                raise ProfileError("author predecessor is not causal")
        sequence_index.add(sequence_key)

        if receipt != {
            "body_cid": body_cid,
            "ingestion_time": receipt["ingestion_time"],
            "key_status_frontier_cid": receipt["key_status_frontier_cid"],
            "log_sequence": expected_log_sequence,
            "appender_key_id": bundle["appender_key_id"],
        }:
            raise ProfileError("receipt binding mismatch")
        verify_signature(appender, RECEIPT_SIGNATURE_DOMAIN, receipt_cid, bytes.fromhex(record["receipt_signature_hex"]))
        events[body_cid] = body
        verified_records[body_cid] = {
            "body_cid": cid_text(body_cid),
            "receipt_cid": cid_text(receipt_cid),
            "log_sequence": expected_log_sequence,
            "body": body,
            "payload": decode_canonical(payload),
            "receipt": receipt,
        }

    order = topological_order(events)
    by_text = {cid_text(raw): record for raw, record in verified_records.items()}
    return order, [by_text[item] for item in order]


def verify_bundle(path: Path) -> list[str]:
    """Verify a Wave01 bundle and return its deterministic replay order."""
    bundle = json.loads(path.read_text(encoding="utf-8"))
    return _verify_bundle_data(bundle)[0]


def verify_bundle_records(path: Path) -> list[dict[str, Any]]:
    """Verify a complete Wave01 bundle before exposing decoded replay records."""
    bundle = json.loads(path.read_text(encoding="utf-8"))
    return _verify_bundle_data(bundle)[1]


def verify_bundle_object(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Verify an embedded Wave01 bundle and expose records only on full success."""
    return _verify_bundle_data(bundle)[1]


def ancestor_contains(events: dict[bytes, dict[str, Any]], parents: list[bytes], target: tuple[str, str, int]) -> bool:
    pending = list(parents)
    seen: set[bytes] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        body = events[current]
        if (body["principal_scope"], body["author_key_id"], body["author_sequence"]) == target:
            return True
        pending.extend(body["parent_event_cids"])
    return False


def topological_order(events: dict[bytes, dict[str, Any]]) -> list[str]:
    indegree = {cid_value: len(body["parent_event_cids"]) for cid_value, body in events.items()}
    children: dict[bytes, list[bytes]] = {cid_value: [] for cid_value in events}
    for child, body in events.items():
        for parent in body["parent_event_cids"]:
            children[parent].append(child)
    ready = sorted(cid_value for cid_value, degree in indegree.items() if degree == 0)
    result: list[bytes] = []
    while ready:
        current = ready.pop(0)
        result.append(current)
        for child in children[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if len(result) != len(events):
        raise ProfileError("cycle detected")
    return [cid_text(value) for value in result]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--emit-replay", action="store_true")
    arguments = parser.parse_args()
    try:
        order = verify_bundle(arguments.bundle)
    except Exception as error:
        print(f"verification failed: {type(error).__name__}", file=sys.stderr)
        return 1
    if arguments.emit_replay:
        print(json.dumps(order, indent=2))
    else:
        print(f"verified {len(order)} events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
