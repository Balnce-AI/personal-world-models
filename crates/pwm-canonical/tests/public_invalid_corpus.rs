use std::{fs, path::PathBuf};

use pwm_canonical::decode_canonical;

#[test]
fn every_published_malformed_cbor_vector_is_rejected() {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../conformance/vectors/wave01-invalid.json");
    let corpus: serde_json::Value = serde_json::from_slice(&fs::read(path).unwrap()).unwrap();
    for case in corpus["canonical_cbor"].as_array().unwrap() {
        let name = case["name"].as_str().unwrap();
        let bytes = hex::decode(case["hex"].as_str().unwrap()).unwrap();
        assert!(
            decode_canonical(&bytes).is_err(),
            "accepted invalid case {name}"
        );
    }
}
