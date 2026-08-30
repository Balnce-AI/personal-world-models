use pwm_canonical::{AppendReceiptBodyCid, EventBodyCid};
use pwm_crypto::{PublicKey, Signature, SigningKey, VerifyError};

#[test]
fn event_signature_is_deterministic_and_verifies() {
    let signer = SigningKey::from_seed([7; 32]);
    let public = signer.public_key();
    let body_cid = EventBodyCid::from_canonical_bytes(&[0xa0]);

    let first = signer.sign_event_body(&body_cid);
    let second = signer.sign_event_body(&body_cid);

    assert_eq!(first, second);
    assert_eq!(first.as_bytes().len(), 64);
    public.verify_event_body(&body_cid, &first).unwrap();
}

#[test]
fn signature_domains_are_not_interchangeable() {
    let signer = SigningKey::from_seed([9; 32]);
    let public = signer.public_key();
    let event = EventBodyCid::from_canonical_bytes(&[0xa0]);
    let receipt = AppendReceiptBodyCid::from_canonical_bytes(&[0xa0]);
    let event_signature = signer.sign_event_body(&event);

    assert_eq!(
        public.verify_append_receipt(&receipt, &event_signature),
        Err(VerifyError::InvalidSignature)
    );
}

#[test]
fn rejects_corrupted_signature_and_public_key() {
    let signer = SigningKey::from_seed([11; 32]);
    let cid = EventBodyCid::from_canonical_bytes(&[0xa1, 0x61, 0x78, 0x01]);
    let mut signature = signer.sign_event_body(&cid).into_bytes();
    signature[0] ^= 1;

    assert_eq!(
        signer
            .public_key()
            .verify_event_body(&cid, &Signature::from_bytes(signature)),
        Err(VerifyError::InvalidSignature)
    );
    assert_eq!(
        PublicKey::from_bytes([0xff; 32]),
        Err(VerifyError::InvalidPublicKey)
    );
}

#[test]
fn exposes_stable_raw_key_and_signature_bytes() {
    let signer = SigningKey::from_seed([1; 32]);
    let cid = EventBodyCid::from_canonical_bytes(&[0xa0]);

    assert_eq!(
        hex::encode(signer.public_key().as_bytes()),
        "8a88e3dd7409f195fd52db2d3cba5d72ca6709bf1d94121bf3748801b40f6f5c"
    );
    assert_eq!(signer.sign_event_body(&cid).as_bytes().len(), 64);
}
