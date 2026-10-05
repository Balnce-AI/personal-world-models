use pwm_canonical::{AppendReceiptBodyCid, CanonicalError, EventBodyCid};
use pwm_crypto::{PublicKey, SIGNATURE_ALGORITHM, Signature};
use pwm_event::{
    AppendReceiptBody, DagError, EventBody, KeyRegistry, MemoryDag, SchemaRegistry,
    SignedAppendReceipt, SignedEvent,
};
use serde::{Deserialize, Serialize};

use crate::{
    ConformanceCommand, ConformanceOutput, SEMANTIC_PROFILE, SemanticErrorCode,
    signed::{evaluate_verified, rejected_output},
};

const TRANSPORT_PROFILE: &str = "pwm-public-provenance-v1";

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SignedSemanticSource {
    pub source_version: String,
    pub source_id: String,
    pub profile: String,
    pub trust_anchor: TrustAnchor,
    pub bundle: VectorBundle,
    pub command: ConformanceCommand,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct TrustAnchor {
    pub key_id: String,
    pub public_key_hex: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct VectorBundle {
    pub profile: String,
    pub appender_key_id: String,
    pub appender_public_key_hex: String,
    pub author_keys: Vec<KeyVector>,
    pub schemas: Vec<SchemaVector>,
    pub records: Vec<RecordVector>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct KeyVector {
    pub key_id: String,
    pub public_key_hex: String,
    pub active_from_log_sequence: u64,
    pub revoked_at_log_sequence: Option<u64>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SchemaVector {
    pub event_kind: String,
    pub schema_version: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RecordVector {
    pub body_cbor_hex: String,
    pub body_cid: String,
    pub event_signature_hex: String,
    pub payload_cbor_hex: String,
    pub receipt_body_cbor_hex: String,
    pub receipt_cid: String,
    pub receipt_signature_hex: String,
}

pub fn evaluate_signed_source_json(input: &str) -> ConformanceOutput {
    let source: SignedSemanticSource = match serde_json::from_str(input) {
        Ok(source) => source,
        Err(_) => {
            return rejected_output(
                "invalid-source".into(),
                SemanticErrorCode::SourceSchemaInvalid,
                None,
            );
        }
    };
    let source_id = source.source_id.clone();
    match evaluate_source(source) {
        Ok(output) => output,
        Err((code, _cid)) => rejected_output(source_id, code, None),
    }
}

fn evaluate_source(source: SignedSemanticSource) -> Result<ConformanceOutput, TransportFailure> {
    validate_source(&source)?;
    let appender_key = public_key(&source.bundle.appender_public_key_hex)?;
    let mut keys = KeyRegistry::new();
    for key in &source.bundle.author_keys {
        keys.activate(
            &key.key_id,
            public_key(&key.public_key_hex)?,
            key.active_from_log_sequence,
        )
        .map_err(map_dag)?;
    }
    for key in &source.bundle.author_keys {
        if let Some(sequence) = key.revoked_at_log_sequence {
            keys.revoke(&key.key_id, sequence).map_err(map_dag)?;
        }
    }
    let schemas = SchemaRegistry::new(
        source
            .bundle
            .schemas
            .iter()
            .map(|item| (&item.event_kind, &item.schema_version)),
    )
    .map_err(map_dag)?;
    let mut dag = MemoryDag::new(&source.bundle.appender_key_id, appender_key);
    for record in &source.bundle.records {
        let cid = Some(record.body_cid.clone());
        let body_bytes = decode_hex(&record.body_cbor_hex).map_err(|code| (code, cid.clone()))?;
        let body = EventBody::from_canonical_bytes(&body_bytes)
            .map_err(|error| with_cid(map_dag(error), cid.clone()))?;
        let body_cid = record
            .body_cid
            .parse::<EventBodyCid>()
            .map_err(|_| (SemanticErrorCode::CidInvalid, cid.clone()))?;
        if EventBodyCid::from_canonical_bytes(&body_bytes) != body_cid {
            return Err((SemanticErrorCode::CidMismatch, cid));
        }
        let event = SignedEvent {
            body,
            body_cid,
            signature_algorithm: SIGNATURE_ALGORITHM.into(),
            signature: Signature::from_bytes(
                hex_array(&record.event_signature_hex).map_err(|code| (code, cid.clone()))?,
            ),
        };
        let receipt_bytes =
            decode_hex(&record.receipt_body_cbor_hex).map_err(|code| (code, cid.clone()))?;
        let receipt = SignedAppendReceipt {
            receipt_body: AppendReceiptBody::from_canonical_bytes(&receipt_bytes)
                .map_err(|error| with_cid(map_dag(error), cid.clone()))?,
            receipt_cid: record
                .receipt_cid
                .parse::<AppendReceiptBodyCid>()
                .map_err(|_| (SemanticErrorCode::CidInvalid, cid.clone()))?,
            signature_algorithm: SIGNATURE_ALGORITHM.into(),
            signature: Signature::from_bytes(
                hex_array(&record.receipt_signature_hex).map_err(|code| (code, cid.clone()))?,
            ),
        };
        let payload = decode_hex(&record.payload_cbor_hex).map_err(|code| (code, cid.clone()))?;
        dag.import_verified(event, &payload, receipt, &keys, &schemas)
            .map_err(|error| with_cid(map_dag(error), cid))?;
    }
    let records = dag.verified_replay().map_err(map_dag)?;
    let anchor = source
        .bundle
        .author_keys
        .iter()
        .find(|key| key.key_id == source.trust_anchor.key_id);
    let first = records.first();
    if anchor.map(|key| key.public_key_hex.as_str())
        != Some(source.trust_anchor.public_key_hex.as_str())
        || first.is_none_or(|record| {
            record.event().body.event_kind != "pwm.genesis"
                || record.event().body.author_key_id != source.trust_anchor.key_id
        })
    {
        return Err((
            SemanticErrorCode::RootTrustMismatch,
            first.map(|record| record.event().body_cid.to_string()),
        ));
    }
    Ok(evaluate_verified(
        source.source_id,
        &records,
        source.command,
    ))
}

type TransportFailure = (SemanticErrorCode, Option<String>);

fn validate_source(source: &SignedSemanticSource) -> Result<(), TransportFailure> {
    if source.source_version != "1.0.0"
        || source.profile != SEMANTIC_PROFILE
        || source.bundle.profile != TRANSPORT_PROFILE
        || source.source_id.is_empty()
        || source.source_id.len() > 256
        || source.bundle.author_keys.is_empty()
        || source.bundle.schemas.is_empty()
        || source.bundle.records.is_empty()
        || source.trust_anchor.key_id.is_empty()
        || decode_hex(&source.trust_anchor.public_key_hex)
            .ok()
            .map(|v| v.len())
            != Some(32)
    {
        return Err((SemanticErrorCode::SourceSchemaInvalid, None));
    }
    Ok(())
}

fn public_key(value: &str) -> Result<PublicKey, TransportFailure> {
    let bytes = hex_array(value).map_err(|code| (code, None))?;
    PublicKey::from_bytes(bytes).map_err(|_| (SemanticErrorCode::PublicKeyInvalid, None))
}

fn decode_hex(value: &str) -> Result<Vec<u8>, SemanticErrorCode> {
    if value.is_empty()
        || !value.len().is_multiple_of(2)
        || value
            .bytes()
            .any(|byte| !byte.is_ascii_hexdigit() || byte.is_ascii_uppercase())
    {
        return Err(SemanticErrorCode::SourceSchemaInvalid);
    }
    hex::decode(value).map_err(|_| SemanticErrorCode::SourceSchemaInvalid)
}

fn hex_array<const N: usize>(value: &str) -> Result<[u8; N], SemanticErrorCode> {
    decode_hex(value)?
        .try_into()
        .map_err(|_| SemanticErrorCode::SourceSchemaInvalid)
}

fn with_cid(failure: TransportFailure, cid: Option<String>) -> TransportFailure {
    (failure.0, cid)
}

fn map_dag(error: DagError) -> TransportFailure {
    let code = match error {
        DagError::Canonical(CanonicalError::NonCanonical) => SemanticErrorCode::CborNonCanonical,
        DagError::Canonical(_) | DagError::MalformedRecord => SemanticErrorCode::CborInvalid,
        DagError::BodyCidMismatch | DagError::PayloadCidMismatch | DagError::ReceiptCidMismatch => {
            SemanticErrorCode::CidMismatch
        }
        DagError::Signature(_) | DagError::UnsupportedSignatureAlgorithm => {
            SemanticErrorCode::SignatureInvalid
        }
        DagError::UnknownKeyFrontier => SemanticErrorCode::KeyFrontierInvalid,
        DagError::MissingParent
        | DagError::CrossScopeParent
        | DagError::MalformedGenesis
        | DagError::ParentsNotSorted
        | DagError::DuplicateParent => SemanticErrorCode::ParentInvalid,
        DagError::InvalidAuthorSequence => SemanticErrorCode::AuthorSequenceInvalid,
        DagError::CycleDetected => SemanticErrorCode::ReplayCycle,
        DagError::UnknownKey
        | DagError::KeyNotActive
        | DagError::KeyRevoked
        | DagError::InvalidKeyTransition
        | DagError::DuplicateKey => SemanticErrorCode::KeyFrontierInvalid,
        DagError::UnknownSchema | DagError::SchemaVersionMismatch | DagError::DuplicateSchema => {
            SemanticErrorCode::UnsupportedSchemaVersion
        }
        DagError::CorruptStorage | DagError::RetryMismatch => SemanticErrorCode::ReceiptInvalid,
        DagError::WrongAppenderKey
        | DagError::SequenceOverflow
        | DagError::Storage
        | DagError::SimulatedCrash => SemanticErrorCode::InternalError,
    };
    (code, None)
}
