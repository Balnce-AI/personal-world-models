//! Public Wave 01 Ed25519 signature profile.
//!
//! This crate intentionally excludes key custody, recovery, operational trust
//! resolution, anti-abuse controls, and production identity internals.

use ed25519_dalek::{Signer, Verifier};
use pwm_canonical::{AppendReceiptBodyCid, EventBodyCid};
use thiserror::Error;

pub const SIGNATURE_ALGORITHM: &str = "Ed25519";
pub const EVENT_SIGNATURE_DOMAIN: &[u8] = b"pwm:event-signature:v1\0";
pub const APPEND_RECEIPT_SIGNATURE_DOMAIN: &[u8] = b"pwm:append-receipt-signature:v1\0";

pub struct SigningKey(ed25519_dalek::SigningKey);

impl SigningKey {
    pub fn from_seed(seed: [u8; 32]) -> Self {
        Self(ed25519_dalek::SigningKey::from_bytes(&seed))
    }

    pub fn public_key(&self) -> PublicKey {
        PublicKey(self.0.verifying_key())
    }

    pub fn sign_event_body(&self, cid: &EventBodyCid) -> Signature {
        self.sign(EVENT_SIGNATURE_DOMAIN, cid.multihash_bytes())
    }

    pub fn sign_append_receipt(&self, cid: &AppendReceiptBodyCid) -> Signature {
        self.sign(APPEND_RECEIPT_SIGNATURE_DOMAIN, cid.multihash_bytes())
    }

    fn sign(&self, domain: &[u8], multihash: &[u8]) -> Signature {
        let mut message = Vec::with_capacity(domain.len() + multihash.len());
        message.extend_from_slice(domain);
        message.extend_from_slice(multihash);
        Signature(self.0.sign(&message).to_bytes())
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PublicKey(ed25519_dalek::VerifyingKey);

impl PublicKey {
    pub fn from_bytes(bytes: [u8; 32]) -> Result<Self, VerifyError> {
        // Ed25519 encodes y in the low 255 bits and the x sign in the high bit.
        // Reject non-canonical y encodings before the curve library can reduce
        // them modulo p = 2^255 - 19.
        let mut y = bytes;
        y[31] &= 0x7f;
        let mut modulus = [0xff; 32];
        modulus[0] = 0xed;
        modulus[31] = 0x7f;
        if little_endian_greater_or_equal(&y, &modulus) {
            return Err(VerifyError::InvalidPublicKey);
        }
        let key = ed25519_dalek::VerifyingKey::from_bytes(&bytes)
            .map_err(|_| VerifyError::InvalidPublicKey)?;
        if key.is_weak() {
            return Err(VerifyError::InvalidPublicKey);
        }
        Ok(Self(key))
    }

    pub fn as_bytes(&self) -> &[u8; 32] {
        self.0.as_bytes()
    }

    pub fn verify_event_body(
        &self,
        cid: &EventBodyCid,
        signature: &Signature,
    ) -> Result<(), VerifyError> {
        self.verify(EVENT_SIGNATURE_DOMAIN, cid.multihash_bytes(), signature)
    }

    pub fn verify_append_receipt(
        &self,
        cid: &AppendReceiptBodyCid,
        signature: &Signature,
    ) -> Result<(), VerifyError> {
        self.verify(
            APPEND_RECEIPT_SIGNATURE_DOMAIN,
            cid.multihash_bytes(),
            signature,
        )
    }

    fn verify(
        &self,
        domain: &[u8],
        multihash: &[u8],
        signature: &Signature,
    ) -> Result<(), VerifyError> {
        let mut message = Vec::with_capacity(domain.len() + multihash.len());
        message.extend_from_slice(domain);
        message.extend_from_slice(multihash);
        let signature = ed25519_dalek::Signature::from_bytes(&signature.0);
        self.0
            .verify(&message, &signature)
            .map_err(|_| VerifyError::InvalidSignature)
    }
}

fn little_endian_greater_or_equal(left: &[u8; 32], right: &[u8; 32]) -> bool {
    for index in (0..32).rev() {
        match left[index].cmp(&right[index]) {
            std::cmp::Ordering::Greater => return true,
            std::cmp::Ordering::Less => return false,
            std::cmp::Ordering::Equal => {}
        }
    }
    true
}

#[derive(Clone, PartialEq, Eq)]
pub struct Signature([u8; 64]);

impl Signature {
    pub fn from_bytes(bytes: [u8; 64]) -> Self {
        Self(bytes)
    }

    pub fn as_bytes(&self) -> &[u8; 64] {
        &self.0
    }

    pub fn into_bytes(self) -> [u8; 64] {
        self.0
    }
}

impl std::fmt::Debug for Signature {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str("Signature([redacted raw bytes])")
    }
}

#[derive(Clone, Debug, Error, PartialEq, Eq)]
pub enum VerifyError {
    #[error("public key is not a valid Ed25519 point")]
    InvalidPublicKey,
    #[error("Ed25519 signature verification failed")]
    InvalidSignature,
}
