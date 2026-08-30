use pwm_canonical::{CanonicalError, Value, decode_canonical, encode};

#[test]
fn encodes_integer_boundaries_with_shortest_forms() {
    let cases = [
        (Value::Unsigned(23), "17"),
        (Value::Unsigned(24), "1818"),
        (Value::Unsigned(255), "18ff"),
        (Value::Unsigned(256), "190100"),
        (Value::Unsigned(65_535), "19ffff"),
        (Value::Unsigned(65_536), "1a00010000"),
        (Value::Unsigned(u64::MAX), "1bffffffffffffffff"),
        (Value::Negative(-1), "20"),
        (Value::Negative(-24), "37"),
        (Value::Negative(-25), "3818"),
        (Value::Negative(i64::MIN), "3b7fffffffffffffff"),
    ];

    for (value, expected) in cases {
        assert_eq!(hex::encode(encode(&value).unwrap()), expected);
    }
}

#[test]
fn sorts_text_map_keys_by_encoded_key_bytes() {
    let value = Value::Map(vec![
        ("aa".into(), Value::Unsigned(1)),
        ("z".into(), Value::Unsigned(2)),
    ]);

    assert_eq!(hex::encode(encode(&value).unwrap()), "a2617a0262616101");
}

#[test]
fn accepts_nfc_and_rejects_decomposed_text() {
    assert_eq!(
        hex::encode(encode(&Value::Text("é".into())).unwrap()),
        "62c3a9"
    );
    assert_eq!(
        encode(&Value::Text("e\u{301}".into())),
        Err(CanonicalError::NonNfcText)
    );
}

#[test]
fn rejects_duplicate_map_keys() {
    let value = Value::Map(vec![
        ("same".into(), Value::Null),
        ("same".into(), Value::Bool(true)),
    ]);

    assert_eq!(encode(&value), Err(CanonicalError::DuplicateMapKey));
}

#[test]
fn rejects_non_profile_and_non_canonical_input() {
    let cases = [
        ("1817", CanonicalError::NonCanonical),
        ("1900ff", CanonicalError::NonCanonical),
        ("3b8000000000000000", CanonicalError::IntegerOutOfRange),
        ("9f01ff", CanonicalError::IndefiniteLength),
        ("bf616101ff", CanonicalError::IndefiniteLength),
        ("7f6161ff", CanonicalError::IndefiniteLength),
        ("f90000", CanonicalError::UnsupportedType),
        ("c001", CanonicalError::UnsupportedType),
        ("f7", CanonicalError::UnsupportedType),
        ("f0", CanonicalError::UnsupportedType),
        ("a10101", CanonicalError::MapKeyNotText),
        ("a2616101616102", CanonicalError::DuplicateMapKey),
        ("a262616101617a02", CanonicalError::NonCanonical),
        ("6365cc81", CanonicalError::NonNfcText),
        ("01ff", CanonicalError::TrailingData),
        ("61ff", CanonicalError::InvalidUtf8),
    ];

    for (encoded, expected) in cases {
        assert_eq!(
            decode_canonical(&hex::decode(encoded).unwrap()),
            Err(expected)
        );
    }
}

#[test]
fn round_trips_nested_profile_values() {
    let value = Value::Map(vec![
        ("bytes".into(), Value::Bytes(vec![0, 1, 2])),
        (
            "items".into(),
            Value::Array(vec![Value::Null, Value::Bool(false), Value::Negative(-9)]),
        ),
    ]);
    let encoded = encode(&value).unwrap();

    assert_eq!(decode_canonical(&encoded).unwrap(), value);
}

#[test]
fn enforces_resource_limits() {
    let mut nested = Value::Null;
    for _ in 0..66 {
        nested = Value::Array(vec![nested]);
    }

    assert_eq!(encode(&nested), Err(CanonicalError::DepthLimitExceeded));
}

#[test]
fn enforces_one_aggregate_item_budget_across_nested_collections() {
    let nested = Value::Array(vec![
        Value::Array(vec![Value::Null; 500_000]),
        Value::Array(vec![Value::Null; 500_000]),
    ]);
    assert_eq!(encode(&nested), Err(CanonicalError::ItemLimitExceeded));

    let mut encoded = vec![0x82, 0x9a, 0x00, 0x07, 0xa1, 0x20];
    encoded.extend(std::iter::repeat_n(0xf6, 500_000));
    encoded.extend_from_slice(&[0x9a, 0x00, 0x07, 0xa1, 0x20]);
    encoded.extend(std::iter::repeat_n(0xf6, 500_000));
    assert_eq!(
        decode_canonical(&encoded),
        Err(CanonicalError::ItemLimitExceeded)
    );
}

#[test]
fn rejects_nested_collection_lengths_before_large_allocation() {
    let nested_array = [0x81, 0x9a, 0x00, 0x0f, 0x42, 0x40];
    assert_eq!(
        decode_canonical(&nested_array),
        Err(CanonicalError::ItemLimitExceeded)
    );

    let nested_map = [0x81, 0xba, 0x00, 0x07, 0xa1, 0x20];
    assert_eq!(
        decode_canonical(&nested_map),
        Err(CanonicalError::ItemLimitExceeded)
    );
}
