use pwm_canonical::{CidError, EventBodyKind, PayloadKind, TypedCid};

#[test]
fn constructs_cidv1_raw_sha256_with_domain_separation() {
    let cid = TypedCid::<EventBodyKind>::from_canonical_bytes(&[0xa0]);
    let bytes = cid.as_bytes();

    assert_eq!(&bytes[..4], &[0x01, 0x55, 0x12, 0x20]);
    assert_eq!(bytes.len(), 36);
    assert!(cid.to_string().starts_with('b'));
}

#[test]
fn type_domain_changes_digest() {
    let event = TypedCid::<EventBodyKind>::from_canonical_bytes(&[0xa0]);
    let payload = TypedCid::<PayloadKind>::from_canonical_bytes(&[0xa0]);

    assert_ne!(event.digest(), payload.digest());
}

#[test]
fn parses_only_cidv1_raw_sha256() {
    let cid = TypedCid::<EventBodyKind>::from_canonical_bytes(&[0xa0]);
    assert_eq!(
        cid.to_string().parse::<TypedCid<EventBodyKind>>().unwrap(),
        cid
    );

    let mut wrong_codec = cid.as_bytes().to_vec();
    wrong_codec[1] = 0x71;
    assert_eq!(
        TypedCid::<EventBodyKind>::from_bytes(&wrong_codec),
        Err(CidError::UnsupportedCodec)
    );
}

#[test]
fn rejects_wrong_multibase_and_noncanonical_base32() {
    let cid = TypedCid::<EventBodyKind>::from_canonical_bytes(&[0xa0]);
    let encoded = cid.to_string();

    assert_eq!(
        encoded[1..].parse::<TypedCid<EventBodyKind>>(),
        Err(CidError::UnsupportedMultibase)
    );
    assert_eq!(
        encoded.to_uppercase().parse::<TypedCid<EventBodyKind>>(),
        Err(CidError::UnsupportedMultibase)
    );
}
