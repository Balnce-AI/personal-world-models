use proptest::prelude::*;
use pwm_canonical::{Value, decode_canonical, encode};

fn leaf() -> impl Strategy<Value = Value> {
    prop_oneof![
        Just(Value::Null),
        any::<bool>().prop_map(Value::Bool),
        any::<u64>().prop_map(Value::Unsigned),
        (i64::MIN..=-1).prop_map(Value::Negative),
        proptest::collection::vec(any::<u8>(), 0..128).prop_map(Value::Bytes),
        "[ -~]{0,64}".prop_map(Value::Text),
    ]
}

fn value() -> impl Strategy<Value = Value> {
    leaf().prop_recursive(4, 256, 8, |inner| {
        prop_oneof![
            proptest::collection::vec(inner.clone(), 0..8).prop_map(Value::Array),
            proptest::collection::btree_map("[a-z]{1,8}", inner, 0..8)
                .prop_map(|map| Value::Map(map.into_iter().collect())),
        ]
    })
}

proptest! {
    #[test]
    fn accepted_values_round_trip_to_one_exact_encoding(value in value()) {
        let bytes = encode(&value).unwrap();
        prop_assert_eq!(encode(&decode_canonical(&bytes).unwrap()).unwrap(), bytes);
    }

    #[test]
    fn trailing_byte_mutations_are_rejected(value in value(), trailing in any::<u8>()) {
        let mut bytes = encode(&value).unwrap();
        bytes.push(trailing);
        prop_assert!(decode_canonical(&bytes).is_err());
    }
}
