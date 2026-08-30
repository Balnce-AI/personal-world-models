//! Restricted deterministic CBOR and typed CID profile for the public PWM
//! provenance interface. This is not the private UOR identity system.

use sha2::{Digest, Sha256};
use std::{collections::HashSet, fmt, marker::PhantomData, str::FromStr};
use thiserror::Error;
use unicode_normalization::UnicodeNormalization;

const MAX_DEPTH: usize = 64;
const MAX_COLLECTION_ITEMS: usize = 1_000_000;
const MAX_BYTE_LENGTH: usize = 16 * 1024 * 1024;
const CID_VERSION: u8 = 0x01;
const RAW_CODEC: u8 = 0x55;
const SHA2_256_CODE: u8 = 0x12;
const SHA2_256_LENGTH: u8 = 0x20;
const CID_LENGTH: usize = 36;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Value {
    Null,
    Bool(bool),
    Unsigned(u64),
    Negative(i64),
    Bytes(Vec<u8>),
    Text(String),
    Array(Vec<Value>),
    Map(Vec<(String, Value)>),
}

#[derive(Clone, Debug, Error, PartialEq, Eq)]
pub enum CanonicalError {
    #[error("text is not NFC-normalized")]
    NonNfcText,
    #[error("map contains a duplicate key")]
    DuplicateMapKey,
    #[error("map key is not text")]
    MapKeyNotText,
    #[error("negative value must be less than zero")]
    InvalidNegative,
    #[error("integer is outside the public profile")]
    IntegerOutOfRange,
    #[error("indefinite-length items are not supported")]
    IndefiniteLength,
    #[error("CBOR type is outside the public profile")]
    UnsupportedType,
    #[error("CBOR is not in deterministic form")]
    NonCanonical,
    #[error("CBOR contains trailing data")]
    TrailingData,
    #[error("text is not valid UTF-8")]
    InvalidUtf8,
    #[error("input ended before the declared item was complete")]
    UnexpectedEnd,
    #[error("nesting depth exceeds the public profile limit")]
    DepthLimitExceeded,
    #[error("collection exceeds the public profile item limit")]
    ItemLimitExceeded,
    #[error("byte or text value exceeds the public profile size limit")]
    ByteLimitExceeded,
}

pub fn encode(value: &Value) -> Result<Vec<u8>, CanonicalError> {
    let mut output = Vec::new();
    let mut remaining_items = MAX_COLLECTION_ITEMS;
    encode_at(value, &mut output, 0, &mut remaining_items)?;
    Ok(output)
}

pub fn decode_canonical(input: &[u8]) -> Result<Value, CanonicalError> {
    let mut decoder = Decoder {
        input,
        position: 0,
        remaining_items: MAX_COLLECTION_ITEMS,
    };
    let value = decoder.value(0)?;
    if decoder.position != input.len() {
        return Err(CanonicalError::TrailingData);
    }
    if encode(&value)? != input {
        return Err(CanonicalError::NonCanonical);
    }
    Ok(value)
}

fn encode_at(
    value: &Value,
    output: &mut Vec<u8>,
    depth: usize,
    remaining_items: &mut usize,
) -> Result<(), CanonicalError> {
    check_depth(depth)?;
    consume_item(remaining_items)?;
    match value {
        Value::Null => output.push(0xf6),
        Value::Bool(false) => output.push(0xf4),
        Value::Bool(true) => output.push(0xf5),
        Value::Unsigned(number) => encode_argument(0, *number, output),
        Value::Negative(number) => {
            if *number >= 0 {
                return Err(CanonicalError::InvalidNegative);
            }
            encode_argument(1, (-1_i128 - i128::from(*number)) as u64, output);
        }
        Value::Bytes(bytes) => {
            check_bytes(bytes.len())?;
            encode_argument(2, bytes.len() as u64, output);
            output.extend_from_slice(bytes);
        }
        Value::Text(text) => encode_text(text, output)?,
        Value::Array(items) => {
            check_items(items.len())?;
            encode_argument(4, items.len() as u64, output);
            for item in items {
                encode_at(item, output, depth + 1, remaining_items)?;
            }
        }
        Value::Map(entries) => {
            check_items(entries.len())?;
            let mut keys = HashSet::with_capacity(entries.len());
            let mut ordered = Vec::with_capacity(entries.len());
            for (key, value) in entries {
                if !keys.insert(key.as_str()) {
                    return Err(CanonicalError::DuplicateMapKey);
                }
                consume_item(remaining_items)?;
                let mut encoded_key = Vec::new();
                encode_text(key, &mut encoded_key)?;
                ordered.push((encoded_key, value));
            }
            ordered.sort_by(|left, right| left.0.cmp(&right.0));
            encode_argument(5, ordered.len() as u64, output);
            for (key, value) in ordered {
                output.extend_from_slice(&key);
                encode_at(value, output, depth + 1, remaining_items)?;
            }
        }
    }
    Ok(())
}

fn encode_text(text: &str, output: &mut Vec<u8>) -> Result<(), CanonicalError> {
    if !text.nfc().eq(text.chars()) {
        return Err(CanonicalError::NonNfcText);
    }
    check_bytes(text.len())?;
    encode_argument(3, text.len() as u64, output);
    output.extend_from_slice(text.as_bytes());
    Ok(())
}

fn encode_argument(major: u8, argument: u64, output: &mut Vec<u8>) {
    let prefix = major << 5;
    match argument {
        0..=23 => output.push(prefix | argument as u8),
        24..=0xff => output.extend_from_slice(&[prefix | 24, argument as u8]),
        0x100..=0xffff => {
            output.push(prefix | 25);
            output.extend_from_slice(&(argument as u16).to_be_bytes());
        }
        0x1_0000..=0xffff_ffff => {
            output.push(prefix | 26);
            output.extend_from_slice(&(argument as u32).to_be_bytes());
        }
        _ => {
            output.push(prefix | 27);
            output.extend_from_slice(&argument.to_be_bytes());
        }
    }
}

fn check_depth(depth: usize) -> Result<(), CanonicalError> {
    if depth > MAX_DEPTH {
        Err(CanonicalError::DepthLimitExceeded)
    } else {
        Ok(())
    }
}

fn check_items(items: usize) -> Result<(), CanonicalError> {
    if items > MAX_COLLECTION_ITEMS {
        Err(CanonicalError::ItemLimitExceeded)
    } else {
        Ok(())
    }
}

fn consume_item(remaining: &mut usize) -> Result<(), CanonicalError> {
    *remaining = remaining
        .checked_sub(1)
        .ok_or(CanonicalError::ItemLimitExceeded)?;
    Ok(())
}

fn check_bytes(length: usize) -> Result<(), CanonicalError> {
    if length > MAX_BYTE_LENGTH {
        Err(CanonicalError::ByteLimitExceeded)
    } else {
        Ok(())
    }
}

struct Decoder<'a> {
    input: &'a [u8],
    position: usize,
    remaining_items: usize,
}

impl Decoder<'_> {
    fn value(&mut self, depth: usize) -> Result<Value, CanonicalError> {
        check_depth(depth)?;
        consume_item(&mut self.remaining_items)?;
        let initial = self.byte()?;
        let major = initial >> 5;
        let additional = initial & 0x1f;
        if additional == 31 {
            return Err(CanonicalError::IndefiniteLength);
        }

        match major {
            0 => Ok(Value::Unsigned(self.argument(additional)?)),
            1 => {
                let encoded = self.argument(additional)?;
                if encoded > i64::MAX as u64 {
                    return Err(CanonicalError::IntegerOutOfRange);
                }
                Ok(Value::Negative(-1 - encoded as i64))
            }
            2 => {
                let length = self.length(additional)?;
                Ok(Value::Bytes(self.take(length)?.to_vec()))
            }
            3 => {
                let length = self.length(additional)?;
                let bytes = self.take(length)?;
                let text = std::str::from_utf8(bytes)
                    .map_err(|_| CanonicalError::InvalidUtf8)?
                    .to_owned();
                if !text.nfc().eq(text.chars()) {
                    return Err(CanonicalError::NonNfcText);
                }
                Ok(Value::Text(text))
            }
            4 => {
                let length = self.collection_length(additional)?;
                self.ensure_item_budget(length)?;
                let mut items = Vec::with_capacity(length);
                for _ in 0..length {
                    items.push(self.value(depth + 1)?);
                }
                Ok(Value::Array(items))
            }
            5 => {
                let length = self.collection_length(additional)?;
                self.ensure_item_budget(
                    length
                        .checked_mul(2)
                        .ok_or(CanonicalError::ItemLimitExceeded)?,
                )?;
                let mut entries = Vec::with_capacity(length);
                let mut keys = HashSet::with_capacity(length);
                for _ in 0..length {
                    let key = match self.value(depth + 1)? {
                        Value::Text(key) => key,
                        _ => return Err(CanonicalError::MapKeyNotText),
                    };
                    if !keys.insert(key.clone()) {
                        return Err(CanonicalError::DuplicateMapKey);
                    }
                    entries.push((key, self.value(depth + 1)?));
                }
                Ok(Value::Map(entries))
            }
            7 if additional == 20 => Ok(Value::Bool(false)),
            7 if additional == 21 => Ok(Value::Bool(true)),
            7 if additional == 22 => Ok(Value::Null),
            _ => Err(CanonicalError::UnsupportedType),
        }
    }

    fn argument(&mut self, additional: u8) -> Result<u64, CanonicalError> {
        let (value, minimum) = match additional {
            0..=23 => return Ok(u64::from(additional)),
            24 => (u64::from(self.byte()?), 24),
            25 => (u64::from(u16::from_be_bytes(self.array()?)), 0x100),
            26 => (u64::from(u32::from_be_bytes(self.array()?)), 0x1_0000),
            27 => (u64::from_be_bytes(self.array()?), 0x1_0000_0000),
            31 => return Err(CanonicalError::IndefiniteLength),
            _ => return Err(CanonicalError::UnsupportedType),
        };
        if value < minimum {
            Err(CanonicalError::NonCanonical)
        } else {
            Ok(value)
        }
    }

    fn length(&mut self, additional: u8) -> Result<usize, CanonicalError> {
        let value = self.argument(additional)?;
        let length = usize::try_from(value).map_err(|_| CanonicalError::ByteLimitExceeded)?;
        check_bytes(length)?;
        Ok(length)
    }

    fn collection_length(&mut self, additional: u8) -> Result<usize, CanonicalError> {
        let value = self.argument(additional)?;
        let length = usize::try_from(value).map_err(|_| CanonicalError::ItemLimitExceeded)?;
        check_items(length)?;
        Ok(length)
    }

    fn ensure_item_budget(&self, required: usize) -> Result<(), CanonicalError> {
        if required > self.remaining_items {
            Err(CanonicalError::ItemLimitExceeded)
        } else {
            Ok(())
        }
    }

    fn byte(&mut self) -> Result<u8, CanonicalError> {
        let byte = *self
            .input
            .get(self.position)
            .ok_or(CanonicalError::UnexpectedEnd)?;
        self.position += 1;
        Ok(byte)
    }

    fn take(&mut self, length: usize) -> Result<&[u8], CanonicalError> {
        let end = self
            .position
            .checked_add(length)
            .ok_or(CanonicalError::UnexpectedEnd)?;
        let bytes = self
            .input
            .get(self.position..end)
            .ok_or(CanonicalError::UnexpectedEnd)?;
        self.position = end;
        Ok(bytes)
    }

    fn array<const N: usize>(&mut self) -> Result<[u8; N], CanonicalError> {
        self.take(N)?
            .try_into()
            .map_err(|_| CanonicalError::UnexpectedEnd)
    }
}

pub trait CidKind {
    const DOMAIN: &'static [u8];
}

#[derive(Clone, Copy, Debug)]
pub struct EventBodyKind;
impl CidKind for EventBodyKind {
    const DOMAIN: &'static [u8] = b"pwm:event-body:v1\0";
}

#[derive(Clone, Copy, Debug)]
pub struct PayloadKind;
impl CidKind for PayloadKind {
    const DOMAIN: &'static [u8] = b"pwm:payload:v1\0";
}

#[derive(Clone, Copy, Debug)]
pub struct AppendReceiptBodyKind;
impl CidKind for AppendReceiptBodyKind {
    const DOMAIN: &'static [u8] = b"pwm:append-receipt-body:v1\0";
}

#[derive(Clone, Copy, Debug)]
pub struct KeyStatusFrontierKind;
impl CidKind for KeyStatusFrontierKind {
    const DOMAIN: &'static [u8] = b"pwm:key-status-frontier:v1\0";
}

pub type EventBodyCid = TypedCid<EventBodyKind>;
pub type PayloadCid = TypedCid<PayloadKind>;
pub type AppendReceiptBodyCid = TypedCid<AppendReceiptBodyKind>;
pub type KeyStatusFrontierCid = TypedCid<KeyStatusFrontierKind>;

#[derive(Clone, Copy)]
pub struct TypedCid<K> {
    bytes: [u8; CID_LENGTH],
    marker: PhantomData<K>,
}

impl<K> TypedCid<K> {
    pub fn from_digest(digest: [u8; 32]) -> Self {
        let mut bytes = [0; CID_LENGTH];
        bytes[..4].copy_from_slice(&[CID_VERSION, RAW_CODEC, SHA2_256_CODE, SHA2_256_LENGTH]);
        bytes[4..].copy_from_slice(&digest);
        Self {
            bytes,
            marker: PhantomData,
        }
    }

    pub fn from_bytes(bytes: &[u8]) -> Result<Self, CidError> {
        if bytes.len() != CID_LENGTH {
            return Err(CidError::InvalidLength);
        }
        if bytes[0] != CID_VERSION {
            return Err(CidError::UnsupportedVersion);
        }
        if bytes[1] != RAW_CODEC {
            return Err(CidError::UnsupportedCodec);
        }
        if bytes[2] != SHA2_256_CODE || bytes[3] != SHA2_256_LENGTH {
            return Err(CidError::UnsupportedHash);
        }
        let mut canonical = [0; CID_LENGTH];
        canonical.copy_from_slice(bytes);
        Ok(Self {
            bytes: canonical,
            marker: PhantomData,
        })
    }

    pub fn as_bytes(&self) -> &[u8; CID_LENGTH] {
        &self.bytes
    }

    pub fn digest(&self) -> &[u8; 32] {
        self.bytes[4..]
            .try_into()
            .expect("CID digest length is fixed")
    }

    pub fn multihash_bytes(&self) -> &[u8] {
        &self.bytes[2..]
    }
}

impl<K: CidKind> TypedCid<K> {
    pub fn from_canonical_bytes(canonical: &[u8]) -> Self {
        let digest = Sha256::new()
            .chain_update(K::DOMAIN)
            .chain_update(canonical)
            .finalize()
            .into();
        Self::from_digest(digest)
    }
}

impl<K> PartialEq for TypedCid<K> {
    fn eq(&self, other: &Self) -> bool {
        self.bytes == other.bytes
    }
}
impl<K> Eq for TypedCid<K> {}
impl<K> std::hash::Hash for TypedCid<K> {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.bytes.hash(state);
    }
}
impl<K> PartialOrd for TypedCid<K> {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}
impl<K> Ord for TypedCid<K> {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.bytes.cmp(&other.bytes)
    }
}
impl<K> fmt::Debug for TypedCid<K> {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_tuple("TypedCid")
            .field(&self.to_string())
            .finish()
    }
}
impl<K> fmt::Display for TypedCid<K> {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "b{}", base32_encode(&self.bytes))
    }
}
impl<K> FromStr for TypedCid<K> {
    type Err = CidError;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        let encoded = value
            .strip_prefix('b')
            .ok_or(CidError::UnsupportedMultibase)?;
        if encoded.is_empty()
            || encoded
                .bytes()
                .any(|byte| !matches!(byte, b'a'..=b'z' | b'2'..=b'7'))
        {
            return Err(CidError::UnsupportedMultibase);
        }
        let bytes = base32_decode(encoded)?;
        let cid = Self::from_bytes(&bytes)?;
        if cid.to_string() != value {
            return Err(CidError::NonCanonicalBase32);
        }
        Ok(cid)
    }
}

#[derive(Clone, Debug, Error, PartialEq, Eq)]
pub enum CidError {
    #[error("CID must use lower-case base32 multibase")]
    UnsupportedMultibase,
    #[error("CID base32 is malformed")]
    InvalidBase32,
    #[error("CID base32 is not canonical")]
    NonCanonicalBase32,
    #[error("CID has the wrong byte length")]
    InvalidLength,
    #[error("only CIDv1 is supported")]
    UnsupportedVersion,
    #[error("only the raw multicodec is supported")]
    UnsupportedCodec,
    #[error("only SHA-256 multihashes are supported")]
    UnsupportedHash,
}

const BASE32: &[u8; 32] = b"abcdefghijklmnopqrstuvwxyz234567";

fn base32_encode(input: &[u8]) -> String {
    let mut output = String::with_capacity((input.len() * 8).div_ceil(5));
    let mut accumulator = 0_u16;
    let mut bits = 0_u8;
    for byte in input {
        accumulator = (accumulator << 8) | u16::from(*byte);
        bits += 8;
        while bits >= 5 {
            bits -= 5;
            output.push(BASE32[((accumulator >> bits) & 0x1f) as usize] as char);
        }
    }
    if bits > 0 {
        output.push(BASE32[((accumulator << (5 - bits)) & 0x1f) as usize] as char);
    }
    output
}

fn base32_decode(input: &str) -> Result<Vec<u8>, CidError> {
    let mut output = Vec::with_capacity(input.len() * 5 / 8);
    let mut accumulator = 0_u32;
    let mut bits = 0_u8;
    for byte in input.bytes() {
        let value = match byte {
            b'a'..=b'z' => byte - b'a',
            b'2'..=b'7' => byte - b'2' + 26,
            _ => return Err(CidError::InvalidBase32),
        };
        accumulator = (accumulator << 5) | u32::from(value);
        bits += 5;
        if bits >= 8 {
            bits -= 8;
            output.push(((accumulator >> bits) & 0xff) as u8);
        }
    }
    if bits > 0 && accumulator & ((1_u32 << bits) - 1) != 0 {
        return Err(CidError::NonCanonicalBase32);
    }
    Ok(output)
}
