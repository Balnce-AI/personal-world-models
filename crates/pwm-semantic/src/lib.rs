//! Deterministic semantic materialization over records already verified by
//! `pwm-event`. This crate does not verify signatures, read storage, consult a
//! clock, or perform physical actions.

use std::collections::{BTreeMap, BTreeSet};

use pwm_canonical::{CanonicalError, Value, decode_canonical};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value as JsonValue};
use thiserror::Error;

mod signed;
mod source;

pub use signed::{
    ConformanceCommand, ConformanceEngine, ConformanceInput, ConformanceOutput, Implementation,
    SignedQuery, evaluate_conformance, evaluate_conformance_json, identify,
};
pub use source::{
    KeyVector, RecordVector, SchemaVector, SignedSemanticSource, TrustAnchor, VectorBundle,
    evaluate_signed_source_json,
};

pub const SEMANTIC_PROFILE: &str = "pwm-signed-semantics-v1";
pub const SEMANTIC_SCHEMA_VERSION: &str = "1.0.0";
pub const ACTUAL_WORLD: &str = "world:actual";

/// Minimal view required from an upstream, cryptographically verified record.
///
/// `pwm-event::VerifiedRecordRef` can implement this trait once it is public by
/// forwarding `event()`, `payload_cbor()`, and `receipt()` into these scalars.
pub trait VerifiedRecord {
    fn schema_version(&self) -> &str;
    fn event_kind(&self) -> &str;
    fn author_key_id(&self) -> &str;
    fn principal_scope(&self) -> &str;
    fn payload_cbor(&self) -> &[u8];
    fn log_sequence(&self) -> u64;
    /// Canonical textual event-body CID. Legacy fixture adapters may omit it.
    fn event_body_cid(&self) -> Option<String> {
        None
    }
    /// Canonical textual parent event-body CIDs in EventBody order.
    fn parent_event_cids(&self) -> Vec<String> {
        Vec::new()
    }
}

/// Owned adapter useful to CLIs, FFI boundaries, and tests.
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct OwnedVerifiedRecord {
    pub schema_version: String,
    pub event_kind: String,
    pub author_key_id: String,
    pub principal_scope: String,
    pub log_sequence: u64,
    /// Canonical CBOR represented as byte integers in JSON.
    pub payload_cbor: Vec<u8>,
    /// Fixture-only provenance metadata. This type does not prove verification.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub event_body_cid: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub parent_event_cids: Vec<String>,
}

impl VerifiedRecord for OwnedVerifiedRecord {
    fn schema_version(&self) -> &str {
        &self.schema_version
    }
    fn event_kind(&self) -> &str {
        &self.event_kind
    }
    fn author_key_id(&self) -> &str {
        &self.author_key_id
    }
    fn principal_scope(&self) -> &str {
        &self.principal_scope
    }
    fn payload_cbor(&self) -> &[u8] {
        &self.payload_cbor
    }
    fn log_sequence(&self) -> u64 {
        self.log_sequence
    }
    fn event_body_cid(&self) -> Option<String> {
        self.event_body_cid.clone()
    }
    fn parent_event_cids(&self) -> Vec<String> {
        self.parent_event_cids.clone()
    }
}

impl VerifiedRecord for pwm_event::VerifiedRecordRef<'_> {
    fn schema_version(&self) -> &str {
        &self.event().body.schema_version
    }
    fn event_kind(&self) -> &str {
        &self.event().body.event_kind
    }
    fn author_key_id(&self) -> &str {
        &self.event().body.author_key_id
    }
    fn principal_scope(&self) -> &str {
        &self.event().body.principal_scope
    }
    fn payload_cbor(&self) -> &[u8] {
        self.payload_bytes()
    }
    fn log_sequence(&self) -> u64 {
        self.receipt().receipt_body.log_sequence
    }
    fn event_body_cid(&self) -> Option<String> {
        Some(self.event().body_cid.to_string())
    }
    fn parent_event_cids(&self) -> Vec<String> {
        self.event()
            .body
            .parent_event_cids
            .iter()
            .map(ToString::to_string)
            .collect()
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PrivacyClass {
    Public,
    Low,
    Personal,
    Sensitive,
    HighlySensitive,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ModelKind {
    #[serde(rename = "SELF")]
    SelfModel,
    Other,
    Relationship,
    World,
    Meta,
    PossibleWorld,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ModelStatus {
    Proposed,
    Accepted,
    Disputed,
    Superseded,
    Revoked,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct Evidence {
    pub evidence_id: String,
    pub privacy_class: PrivacyClass,
    #[serde(default)]
    pub value: JsonValue,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct Declassification {
    pub declassification_id: String,
    pub model_id: String,
    pub output_privacy_class: PrivacyClass,
    pub released_fields: BTreeSet<String>,
    pub policy_ref: String,
    pub approved_at_log_sequence: u64,
    pub revoked_at_log_sequence: Option<u64>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct Model {
    pub model_id: String,
    pub family_id: String,
    pub kind: ModelKind,
    pub subject_ids: BTreeSet<String>,
    pub perspective: String,
    pub state: BTreeMap<String, JsonValue>,
    pub status: ModelStatus,
    pub confidence_ppm: u64,
    pub privacy_class: PrivacyClass,
    pub effective_privacy_class: PrivacyClass,
    pub evidence_refs: BTreeSet<String>,
    pub dependency_refs: BTreeSet<String>,
    pub derivation_refs: BTreeSet<String>,
    pub proposal_log_sequence: u64,
    pub review_log_sequence: Option<u64>,
    pub accepted_log_sequence: Option<u64>,
    pub previous_model_id: Option<String>,
    pub world_id: String,
    pub parent_world_id: Option<String>,
    pub valid_from_ns: Option<i64>,
    pub valid_to_ns: Option<i64>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct Review {
    pub model_id: String,
    pub decision: String,
    pub reviewer: String,
    pub log_sequence: u64,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct Contradiction {
    pub contradiction_id: String,
    pub model_ids: BTreeSet<String>,
    pub status: String,
    pub proposal_log_sequence: u64,
    pub review_log_sequence: Option<u64>,
    pub resolution: Option<JsonValue>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct TopologyEdge {
    pub edge_id: String,
    pub source_model_id: String,
    pub edge_type: String,
    pub target_model_id: String,
    pub effective_privacy_class: PrivacyClass,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct PossibleWorld {
    pub world_id: String,
    pub parent_world_id: String,
    pub base_state_id: String,
    pub base_time_ns: i64,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct QueryAuthority {
    pub authority_id: String,
    pub principal_id: String,
    pub recipient_id: String,
    pub purpose: String,
    pub allowed_subjects: BTreeSet<String>,
    pub allowed_families: BTreeSet<String>,
    pub allowed_fields: BTreeSet<String>,
    pub world_id: String,
    pub max_privacy_class: PrivacyClass,
    pub valid_from_ns: i64,
    pub valid_to_ns: i64,
    pub revoked_at_log_sequence: Option<u64>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct HplRequest {
    pub request_id: String,
    pub principal_id: String,
    pub recipient_id: String,
    pub purpose: String,
    pub requested_fields: BTreeSet<String>,
    pub max_privacy_class: PrivacyClass,
    pub at_ns: i64,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct HplProjection {
    pub projection_id: String,
    pub request_id: String,
    pub authority_id: String,
    pub principal_id: String,
    pub recipient_id: String,
    pub purpose: String,
    pub fields: BTreeMap<String, JsonValue>,
    pub field_privacy: BTreeMap<String, PrivacyClass>,
    pub issued_at_ns: i64,
    pub expires_at_ns: i64,
    pub revoked_at_log_sequence: Option<u64>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct PrincipalGrant {
    pub grant_id: String,
    pub principal_id: String,
    pub key_id: String,
    pub principal_scope: String,
    pub operations: BTreeSet<String>,
    pub capabilities: BTreeSet<String>,
    pub grant_class: String,
    pub active_from_log_sequence: u64,
    pub revoked_at_log_sequence: Option<u64>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct ModelFamily {
    pub family_id: String,
    pub allowed_kinds: BTreeSet<ModelKind>,
}

#[derive(Clone, Debug, Default, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct SemanticState {
    pub principals: BTreeMap<String, String>,
    pub grants: Vec<PrincipalGrant>,
    pub families: BTreeMap<String, ModelFamily>,
    pub evidence: BTreeMap<String, Evidence>,
    pub policies: BTreeSet<String>,
    pub proposals: BTreeMap<String, Model>,
    pub reviews: BTreeMap<String, Review>,
    pub models: BTreeMap<String, Model>,
    pub historical_models: BTreeMap<String, Model>,
    pub declassifications: BTreeMap<String, Declassification>,
    pub contradictions: BTreeMap<String, Contradiction>,
    pub topology: BTreeMap<String, TopologyEdge>,
    pub possible_worlds: BTreeMap<String, PossibleWorld>,
    pub query_authorities: BTreeMap<String, QueryAuthority>,
    pub hpl_requests: BTreeMap<String, HplRequest>,
    pub hpl_projections: BTreeMap<String, HplProjection>,
    pub last_log_sequence: Option<u64>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct SemanticQuery {
    pub authority_id: String,
    pub principal_id: String,
    pub recipient_id: String,
    pub purpose: String,
    #[serde(default)]
    pub subjects: BTreeSet<String>,
    #[serde(default)]
    pub families: BTreeSet<String>,
    #[serde(default)]
    pub fields: BTreeSet<String>,
    pub world_id: String,
    pub max_privacy_class: PrivacyClass,
    pub at_ns: i64,
    #[serde(default)]
    pub include_disputed: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct QueryModel {
    pub model_id: String,
    pub family_id: String,
    pub kind: ModelKind,
    pub subject_ids: BTreeSet<String>,
    pub state: BTreeMap<String, JsonValue>,
    pub status: ModelStatus,
    pub effective_privacy_class: PrivacyClass,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct QueryResult {
    pub authority_id: String,
    pub world_id: String,
    pub models: Vec<QueryModel>,
    pub edges: Vec<TopologyEdge>,
    pub contradictions: Vec<Contradiction>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct EvaluationInput {
    pub records: Vec<OwnedVerifiedRecord>,
    pub query: Option<SemanticQuery>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct EvaluationOutput {
    pub state: SemanticState,
    pub query: Option<QueryResult>,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq, Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SemanticErrorCode {
    SourceSchemaInvalid,
    CborInvalid,
    CborNonCanonical,
    CidInvalid,
    CidMismatch,
    PublicKeyInvalid,
    SignatureInvalid,
    KeyFrontierInvalid,
    ReceiptInvalid,
    ParentInvalid,
    AuthorSequenceInvalid,
    ReplayCycle,
    RootTrustMismatch,
    UnsupportedEventKind,
    PayloadEnvelopeInvalid,
    PayloadFieldInvalid,
    GrantNotFound,
    GrantNotActive,
    PrincipalAmbiguous,
    CapabilityNotGranted,
    ReferenceNotFound,
    IdentifierConflict,
    LifecyclePreconditionMissing,
    ReviewSeparationViolation,
    WorldScopeViolation,
    TopologyCycle,
    AuthorityScopeViolation,
    CommandUnsupported,
    OutputSchemaInvalid,
    InternalError,
    // Compatibility names retained for callers while v1 codes above are used
    // by the signed semantic path.
    RecordSequence,
    PayloadCbor,
    EnvelopeShape,
    UnsupportedProfile,
    UnsupportedSchemaVersion,
    AuthorizationMissing,
    AuthorizationScopeMismatch,
    AuthorizationOperationDenied,
    UnsupportedOperation,
    InvalidField,
    DuplicateId,
    MissingReference,
    InvalidLifecycle,
    InvalidModelKind,
    FamilyKindNotAllowed,
    PossibleWorldScopeViolation,
    PrivacyClassUnknown,
    PrivacyEffectiveClassMismatch,
    DeclassificationInvalid,
    DependencyCycle,
    AuthorityBindingMismatch,
    AuthorityExpired,
    AuthorityRevoked,
    QueryUnauthorized,
    HplRequestMissing,
}

#[derive(Clone, Debug, Error, PartialEq, Eq, Serialize)]
#[error("{code:?} at log sequence {log_sequence}: {message}")]
#[serde(rename_all = "camelCase")]
pub struct SemanticError {
    pub code: SemanticErrorCode,
    pub log_sequence: u64,
    pub event_kind: String,
    pub message: String,
}

impl SemanticError {
    fn at(code: SemanticErrorCode, sequence: u64, kind: &str, message: impl Into<String>) -> Self {
        Self {
            code,
            log_sequence: sequence,
            event_kind: kind.into(),
            message: message.into(),
        }
    }
}

#[derive(Clone, Debug, Default)]
pub struct SemanticEngine {
    state: SemanticState,
}

impl SemanticEngine {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn from_state(state: SemanticState) -> Self {
        Self { state }
    }
    pub fn state(&self) -> &SemanticState {
        &self.state
    }
    pub fn into_state(self) -> SemanticState {
        self.state
    }

    /// Applies records in receipt order. Each record is atomic; on failure the
    /// state remains at the last successfully reduced record.
    pub fn reduce<'a, R: VerifiedRecord + 'a>(
        records: impl IntoIterator<Item = &'a R>,
    ) -> Result<SemanticState, SemanticError> {
        let mut engine = Self::new();
        for record in records {
            engine.apply(record)?;
        }
        Ok(engine.into_state())
    }

    pub fn apply<R: VerifiedRecord>(&mut self, record: &R) -> Result<(), SemanticError> {
        let sequence = record.log_sequence();
        let kind = record.event_kind();
        let expected = self
            .state
            .last_log_sequence
            .map_or(0, |value| value.saturating_add(1));
        if sequence != expected {
            return Err(SemanticError::at(
                SemanticErrorCode::ReceiptInvalid,
                sequence,
                kind,
                "records must be contiguous in receipt log order",
            ));
        }
        if record.schema_version() != SEMANTIC_SCHEMA_VERSION {
            return err(
                SemanticErrorCode::UnsupportedSchemaVersion,
                sequence,
                kind,
                "unsupported event schema version",
            );
        }
        let envelope = decode_envelope(record.payload_cbor(), sequence, kind)?;
        let mut next = self.state.clone();
        if kind == "pwm.genesis" {
            if sequence != 0 || !next.grants.is_empty() {
                return Err(SemanticError::at(
                    SemanticErrorCode::InvalidLifecycle,
                    sequence,
                    kind,
                    "genesis must be the first semantic record",
                ));
            }
            apply_genesis(&mut next, record, &envelope.data)?;
        } else {
            authorize(&next, record)?;
            apply_operation(&mut next, record, &envelope)?;
        }
        next.last_log_sequence = Some(sequence);
        self.state = next;
        Ok(())
    }

    pub fn query(&self, query: &SemanticQuery) -> Result<QueryResult, SemanticError> {
        execute_query(&self.state, query)
    }
}

struct Envelope {
    data: BTreeMap<String, JsonValue>,
    valid_from_ns: Option<i64>,
    valid_to_ns: Option<i64>,
}

fn decode_envelope(bytes: &[u8], sequence: u64, kind: &str) -> Result<Envelope, SemanticError> {
    let value = decode_canonical(bytes).map_err(|error| {
        SemanticError::at(
            if error == CanonicalError::NonCanonical {
                SemanticErrorCode::CborNonCanonical
            } else {
                SemanticErrorCode::CborInvalid
            },
            sequence,
            kind,
            canonical_message(error),
        )
    })?;
    let Value::Map(entries) = value else {
        return err(
            SemanticErrorCode::PayloadEnvelopeInvalid,
            sequence,
            kind,
            "payload envelope must be a map",
        );
    };
    let fields: BTreeMap<_, _> = entries.into_iter().collect();
    let expected: BTreeSet<_> = [
        "profile",
        "schema_version",
        "data",
        "valid_from_ns",
        "valid_to_ns",
    ]
    .into_iter()
    .collect();
    if fields.keys().map(String::as_str).collect::<BTreeSet<_>>() != expected {
        return err(
            SemanticErrorCode::PayloadEnvelopeInvalid,
            sequence,
            kind,
            "payload envelope must contain exactly profile, schema_version, data, valid_from_ns, valid_to_ns",
        );
    }
    match fields.get("profile") {
        Some(Value::Text(profile)) if profile == SEMANTIC_PROFILE => {}
        _ => {
            return err(
                SemanticErrorCode::PayloadEnvelopeInvalid,
                sequence,
                kind,
                "unsupported semantic payload profile",
            );
        }
    }
    match fields.get("schema_version") {
        Some(Value::Text(version)) if version == SEMANTIC_SCHEMA_VERSION => {}
        _ => {
            return err(
                SemanticErrorCode::UnsupportedSchemaVersion,
                sequence,
                kind,
                "unsupported semantic schema version",
            );
        }
    }
    let Value::Map(data) = fields.get("data").expect("shape checked") else {
        return err(
            SemanticErrorCode::PayloadEnvelopeInvalid,
            sequence,
            kind,
            "envelope data must be a map",
        );
    };
    let valid_from_ns = optional_i64(
        fields.get("valid_from_ns").expect("shape checked"),
        sequence,
        kind,
        "valid_from_ns",
    )?;
    let valid_to_ns = optional_i64(
        fields.get("valid_to_ns").expect("shape checked"),
        sequence,
        kind,
        "valid_to_ns",
    )?;
    if matches!((valid_from_ns, valid_to_ns), (Some(from), Some(to)) if from >= to) {
        return err(
            SemanticErrorCode::InvalidField,
            sequence,
            kind,
            "valid time must be a non-empty half-open interval",
        );
    }
    Ok(Envelope {
        data: data
            .iter()
            .map(|(key, value)| Ok((key.clone(), cbor_to_json(value)?)))
            .collect::<Result<_, SemanticError>>()?,
        valid_from_ns,
        valid_to_ns,
    })
}

fn canonical_message(error: CanonicalError) -> String {
    format!("canonical CBOR rejected: {error}")
}

fn optional_i64(
    value: &Value,
    sequence: u64,
    kind: &str,
    field: &str,
) -> Result<Option<i64>, SemanticError> {
    match value {
        Value::Null => Ok(None),
        Value::Unsigned(number) => i64::try_from(*number).map(Some).map_err(|_| {
            SemanticError::at(
                SemanticErrorCode::InvalidField,
                sequence,
                kind,
                format!("{field} exceeds i64"),
            )
        }),
        Value::Negative(number) => Ok(Some(*number)),
        _ => err(
            SemanticErrorCode::InvalidField,
            sequence,
            kind,
            format!("{field} must be null or integer"),
        ),
    }
}

fn cbor_to_json(value: &Value) -> Result<JsonValue, SemanticError> {
    Ok(match value {
        Value::Null => JsonValue::Null,
        Value::Bool(value) => JsonValue::Bool(*value),
        Value::Unsigned(value) => JsonValue::Number((*value).into()),
        Value::Negative(value) => JsonValue::Number((*value).into()),
        Value::Text(value) => JsonValue::String(value.clone()),
        Value::Bytes(bytes) => {
            JsonValue::Array(bytes.iter().copied().map(JsonValue::from).collect())
        }
        Value::Array(values) => {
            JsonValue::Array(values.iter().map(cbor_to_json).collect::<Result<_, _>>()?)
        }
        Value::Map(entries) => JsonValue::Object(
            entries
                .iter()
                .map(|(key, value)| Ok((key.clone(), cbor_to_json(value)?)))
                .collect::<Result<Map<_, _>, SemanticError>>()?,
        ),
    })
}

fn apply_genesis<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let grants = array(data, "grants", record)?;
    for item in grants {
        let object = object_value(item, "grant", record)?;
        let signed_profile = object.contains_key("grant_id");
        let key_id_field = if signed_profile { "key_id" } else { "keyId" };
        let scope_field = if signed_profile {
            "scope_id"
        } else {
            "principalScope"
        };
        let active_field = if signed_profile {
            "valid_from_log_sequence"
        } else {
            "activeFromLogSequence"
        };
        let revoked_field = if signed_profile {
            "valid_to_log_sequence"
        } else {
            "revokedAtLogSequence"
        };
        let key_id = string(object, key_id_field, record)?;
        let principal_scope = string(object, scope_field, record)?;
        let grant = PrincipalGrant {
            grant_id: optional_string(
                object,
                if signed_profile {
                    "grant_id"
                } else {
                    "grantId"
                },
                record,
            )?
            .unwrap_or_else(|| format!("grant:{principal_scope}:{key_id}")),
            principal_id: optional_string(
                object,
                if signed_profile {
                    "principal_id"
                } else {
                    "principalId"
                },
                record,
            )?
            .unwrap_or_else(|| principal_scope.clone()),
            key_id,
            principal_scope,
            operations: string_set(object, "operations", record)?,
            capabilities: optional_string_set(object, "capabilities", record)?,
            grant_class: optional_string(
                object,
                if signed_profile {
                    "grant_class"
                } else {
                    "grantClass"
                },
                record,
            )?
            .unwrap_or_else(|| "ROOT".into()),
            active_from_log_sequence: optional_u64_field(object, active_field, record)?
                .unwrap_or(0),
            revoked_at_log_sequence: optional_u64_field(object, revoked_field, record)?,
        };
        if grant.operations.is_empty()
            || grant.key_id.is_empty()
            || grant.principal_scope.is_empty()
        {
            return err_for(
                SemanticErrorCode::InvalidField,
                record,
                "grant key, scope, and operations must be non-empty",
            );
        }
        if matches!(grant.revoked_at_log_sequence, Some(revoked) if revoked < grant.active_from_log_sequence)
        {
            return err_for(
                SemanticErrorCode::InvalidField,
                record,
                "grant revocation precedes activation",
            );
        }
        state.grants.push(grant);
    }
    state.grants.sort_by(|a, b| {
        (&a.principal_scope, &a.key_id, a.active_from_log_sequence).cmp(&(
            &b.principal_scope,
            &b.key_id,
            b.active_from_log_sequence,
        ))
    });
    if !state.grants.iter().any(|grant| {
        grant.key_id == record.author_key_id() && grant.principal_scope == record.principal_scope()
    }) {
        return err_for(
            SemanticErrorCode::AuthorizationMissing,
            record,
            "genesis must grant its author in its principal scope",
        );
    }
    Ok(())
}

fn authorize<R: VerifiedRecord>(state: &SemanticState, record: &R) -> Result<(), SemanticError> {
    let matching_key: Vec<_> = state
        .grants
        .iter()
        .filter(|grant| grant.key_id == record.author_key_id())
        .collect();
    if matching_key.is_empty() {
        return err_for(
            SemanticErrorCode::AuthorizationMissing,
            record,
            "author key has no principal grant",
        );
    }
    let matching_scope: Vec<_> = matching_key
        .into_iter()
        .filter(|grant| grant.principal_scope == record.principal_scope())
        .collect();
    if matching_scope.is_empty() {
        return err_for(
            SemanticErrorCode::AuthorizationScopeMismatch,
            record,
            "author key is not granted for principal scope",
        );
    }
    let sequence = record.log_sequence();
    let active = matching_scope.into_iter().filter(|grant| {
        grant.active_from_log_sequence <= sequence
            && grant
                .revoked_at_log_sequence
                .is_none_or(|revoked| sequence < revoked)
    });
    if active.into_iter().any(|grant| {
        grant
            .operations
            .iter()
            .any(|operation| operation_matches(operation, record.event_kind()))
    }) {
        return Ok(());
    }
    err_for(
        SemanticErrorCode::AuthorizationOperationDenied,
        record,
        "operation is not granted at receipt log sequence",
    )
}

fn operation_matches(grant: &str, operation: &str) -> bool {
    grant == "*"
        || grant == operation
        || grant.strip_suffix(".*").is_some_and(|prefix| {
            operation.starts_with(prefix) && operation.as_bytes().get(prefix.len()) == Some(&b'.')
        })
}

fn apply_operation<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    envelope: &Envelope,
) -> Result<(), SemanticError> {
    match record.event_kind() {
        "pwm.evidence.recorded" => evidence_recorded(state, record, &envelope.data),
        "pwm.policy.recorded" => policy_recorded(state, record, &envelope.data),
        "pwm.family.registered" => family_registered(state, record, &envelope.data),
        "pwm.model.proposed" => model_proposed(state, record, envelope),
        "pwm.model.reviewed" => model_reviewed(state, record, &envelope.data),
        "pwm.model.accepted" => model_committed(state, record, &envelope.data, false),
        "pwm.model.updated" => model_committed(state, record, &envelope.data, true),
        "pwm.model.disputed" => {
            model_transition(state, record, &envelope.data, ModelStatus::Disputed)
        }
        "pwm.model.revoked" => {
            model_transition(state, record, &envelope.data, ModelStatus::Revoked)
        }
        "pwm.declassification.approved" => declassification_approved(state, record, &envelope.data),
        "pwm.declassification.revoked" => declassification_revoked(state, record, &envelope.data),
        "pwm.contradiction.proposed" => contradiction_proposed(state, record, &envelope.data),
        "pwm.contradiction.reviewed" => contradiction_reviewed(state, record, &envelope.data),
        "pwm.contradiction.accepted" => contradiction_accepted(state, record, &envelope.data),
        "pwm.contradiction.resolved" => contradiction_resolved(state, record, &envelope.data),
        "pwm.topology.edge-added" => topology_added(state, record, &envelope.data),
        "pwm.possible-world.created" => possible_world_created(state, record, &envelope.data),
        "pwm.query.authorized" => query_authorized(state, record, &envelope.data),
        "pwm.query.authorization-revoked" => query_authority_revoked(state, record, &envelope.data),
        "hpl.projection.requested" => hpl_requested(state, record, &envelope.data),
        "hpl.projection.authorized" => hpl_authorized(state, record, &envelope.data),
        "hpl.projection.issued" => hpl_issued(state, record, &envelope.data),
        "hpl.projection.revoked" => hpl_revoked(state, record, &envelope.data),
        _ => err_for(
            SemanticErrorCode::UnsupportedOperation,
            record,
            "event kind is unsupported by signed semantics v1",
        ),
    }
}

fn evidence_recorded<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "evidenceId", record)?;
    unique(&state.evidence, &id, record)?;
    state.evidence.insert(
        id.clone(),
        Evidence {
            evidence_id: id,
            privacy_class: privacy(data, "privacyClass", record)?,
            value: data.get("value").cloned().unwrap_or(JsonValue::Null),
        },
    );
    Ok(())
}

fn policy_recorded<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "policyId", record)?;
    if !state.policies.insert(id) {
        return err_for(
            SemanticErrorCode::DuplicateId,
            record,
            "policy already exists",
        );
    }
    Ok(())
}

fn family_registered<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "familyId", record)?;
    unique(&state.families, &id, record)?;
    let values = array(data, "allowedKinds", record)?;
    let mut allowed_kinds = BTreeSet::new();
    for value in values {
        let kind = serde_json::from_value(value.clone()).map_err(|_| {
            SemanticError::at(
                SemanticErrorCode::InvalidModelKind,
                record.log_sequence(),
                record.event_kind(),
                "invalid family model kind",
            )
        })?;
        if !allowed_kinds.insert(kind) {
            return err_for(
                SemanticErrorCode::InvalidField,
                record,
                "allowedKinds must be unique",
            );
        }
    }
    if allowed_kinds.is_empty() {
        return err_for(
            SemanticErrorCode::InvalidField,
            record,
            "family must allow at least one kind",
        );
    }
    state.families.insert(
        id.clone(),
        ModelFamily {
            family_id: id,
            allowed_kinds,
        },
    );
    Ok(())
}

fn model_proposed<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    envelope: &Envelope,
) -> Result<(), SemanticError> {
    let data = &envelope.data;
    let id = string(data, "modelId", record)?;
    if state.proposals.contains_key(&id)
        || state.models.contains_key(&id)
        || state.historical_models.contains_key(&id)
    {
        return err_for(
            SemanticErrorCode::DuplicateId,
            record,
            "model id already exists",
        );
    }
    let kind: ModelKind = enum_field(data, "kind", record, SemanticErrorCode::InvalidModelKind)?;
    let family_id = string(data, "familyId", record)?;
    if state
        .families
        .get(&family_id)
        .is_some_and(|family| !family.allowed_kinds.contains(&kind))
    {
        return err_for(
            SemanticErrorCode::FamilyKindNotAllowed,
            record,
            "model kind is not allowed by registered family",
        );
    }
    let subjects = string_set(data, "subjectIds", record)?;
    let perspective = string(data, "perspective", record)?;
    validate_model_kind(kind, &subjects, &perspective, data, state, record)?;
    let evidence_refs = optional_string_set(data, "evidenceRefs", record)?;
    let dependency_refs = optional_string_set(data, "dependencyRefs", record)?;
    let derivation_refs = optional_string_set(data, "derivationRefs", record)?;
    for evidence in &evidence_refs {
        if !state.evidence.contains_key(evidence) {
            return err_for(
                SemanticErrorCode::MissingReference,
                record,
                format!("unknown evidence: {evidence}"),
            );
        }
    }
    for dependency in &dependency_refs {
        if !state.models.contains_key(dependency) {
            return err_for(
                SemanticErrorCode::MissingReference,
                record,
                format!("unknown accepted dependency: {dependency}"),
            );
        }
    }
    let declared = privacy(data, "privacyClass", record)?;
    let mut effective = declared;
    for evidence in &evidence_refs {
        effective = effective.max(state.evidence[evidence].privacy_class);
    }
    for dependency in &dependency_refs {
        effective = effective.max(state.models[dependency].effective_privacy_class);
    }
    if let Some(claimed) =
        optional_enum_field::<PrivacyClass, _>(data, "effectivePrivacyClass", record)?
        && claimed != effective
    {
        return err_for(
            SemanticErrorCode::PrivacyEffectiveClassMismatch,
            record,
            "claimed effective privacy does not equal source join",
        );
    }
    let world_id = optional_string(data, "worldId", record)?.unwrap_or_else(|| ACTUAL_WORLD.into());
    let parent_world_id = optional_string(data, "parentWorldId", record)?;
    if kind == ModelKind::PossibleWorld {
        if world_id == ACTUAL_WORLD
            || !state.possible_worlds.contains_key(&world_id)
            || parent_world_id.as_deref()
                != state
                    .possible_worlds
                    .get(&world_id)
                    .map(|world| world.parent_world_id.as_str())
        {
            return err_for(
                SemanticErrorCode::PossibleWorldScopeViolation,
                record,
                "possible-world model must bind an existing non-actual world and its parent",
            );
        }
    } else if world_id != ACTUAL_WORLD {
        return err_for(
            SemanticErrorCode::PossibleWorldScopeViolation,
            record,
            "only POSSIBLE_WORLD models may enter a hypothetical world",
        );
    }
    let confidence_ppm = optional_u64_field(data, "confidencePpm", record)?.unwrap_or(1_000_000);
    if confidence_ppm > 1_000_000 {
        return err_for(
            SemanticErrorCode::InvalidField,
            record,
            "confidencePpm exceeds 1,000,000",
        );
    }
    let model = Model {
        model_id: id.clone(),
        family_id,
        kind,
        subject_ids: subjects,
        perspective,
        state: optional_object(data, "state", record)?,
        status: ModelStatus::Proposed,
        confidence_ppm,
        privacy_class: declared,
        effective_privacy_class: effective,
        evidence_refs,
        dependency_refs,
        derivation_refs,
        proposal_log_sequence: record.log_sequence(),
        review_log_sequence: None,
        accepted_log_sequence: None,
        previous_model_id: optional_string(data, "previousModelId", record)?,
        world_id,
        parent_world_id,
        valid_from_ns: envelope.valid_from_ns,
        valid_to_ns: envelope.valid_to_ns,
    };
    state.proposals.insert(id, model);
    Ok(())
}

fn validate_model_kind<R: VerifiedRecord>(
    kind: ModelKind,
    subjects: &BTreeSet<String>,
    perspective: &str,
    data: &BTreeMap<String, JsonValue>,
    state: &SemanticState,
    record: &R,
) -> Result<(), SemanticError> {
    if subjects.is_empty() {
        return err_for(
            SemanticErrorCode::InvalidModelKind,
            record,
            "models require at least one subject",
        );
    }
    match kind {
        ModelKind::SelfModel if !subjects.contains(perspective) => {
            return err_for(
                SemanticErrorCode::InvalidModelKind,
                record,
                "SELF perspective must be a subject",
            );
        }
        ModelKind::Other if subjects.contains(perspective) => {
            return err_for(
                SemanticErrorCode::InvalidModelKind,
                record,
                "OTHER perspective must be outside modeled subjects",
            );
        }
        ModelKind::Relationship if subjects.len() < 2 => {
            return err_for(
                SemanticErrorCode::InvalidModelKind,
                record,
                "RELATIONSHIP requires at least two distinct subjects",
            );
        }
        ModelKind::Meta => {
            let target = string(data, "targetModelId", record)?;
            if !state.models.contains_key(&target) {
                return err_for(
                    SemanticErrorCode::MissingReference,
                    record,
                    "META target must be an accepted model",
                );
            }
        }
        ModelKind::World
        | ModelKind::PossibleWorld
        | ModelKind::SelfModel
        | ModelKind::Other
        | ModelKind::Relationship => {}
    }
    Ok(())
}

fn model_reviewed<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "modelId", record)?;
    let proposal = state.proposals.get(&id).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::MissingReference,
            record.log_sequence(),
            record.event_kind(),
            "review references unknown proposal",
        )
    })?;
    if proposal.review_log_sequence.is_some() {
        return err_for(
            SemanticErrorCode::InvalidLifecycle,
            record,
            "proposal already reviewed",
        );
    }
    let decision = string(data, "decision", record)?;
    if decision != "ACCEPT" && decision != "REJECT" {
        return err_for(
            SemanticErrorCode::InvalidField,
            record,
            "review decision must be ACCEPT or REJECT",
        );
    }
    let reviewer = string(data, "reviewer", record)?;
    if reviewer != proposal.perspective {
        return err_for(
            SemanticErrorCode::AuthorizationScopeMismatch,
            record,
            "reviewer must equal model perspective",
        );
    }
    state
        .proposals
        .get_mut(&id)
        .expect("checked")
        .review_log_sequence = Some(record.log_sequence());
    state.reviews.insert(
        id.clone(),
        Review {
            model_id: id,
            decision,
            reviewer,
            log_sequence: record.log_sequence(),
        },
    );
    Ok(())
}

fn model_committed<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
    update: bool,
) -> Result<(), SemanticError> {
    let id = string(data, "modelId", record)?;
    let proposal = state.proposals.get(&id).cloned().ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::MissingReference,
            record.log_sequence(),
            record.event_kind(),
            "acceptance references unknown proposal",
        )
    })?;
    let review = state.reviews.get(&id).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::MissingReference,
            record.log_sequence(),
            record.event_kind(),
            "acceptance requires review",
        )
    })?;
    if review.decision != "ACCEPT" || proposal.status != ModelStatus::Proposed {
        return err_for(
            SemanticErrorCode::InvalidLifecycle,
            record,
            "acceptance requires an ACCEPT review of a proposal",
        );
    }
    if update != proposal.previous_model_id.is_some() {
        return err_for(
            SemanticErrorCode::InvalidLifecycle,
            record,
            "updated requires previousModelId; accepted forbids it",
        );
    }
    if let Some(previous) = &proposal.previous_model_id {
        let mut prior = state.models.remove(previous).ok_or_else(|| {
            SemanticError::at(
                SemanticErrorCode::MissingReference,
                record.log_sequence(),
                record.event_kind(),
                "previous model is not current",
            )
        })?;
        prior.status = ModelStatus::Superseded;
        state.historical_models.insert(previous.clone(), prior);
    }
    let mut accepted = proposal;
    accepted.status = ModelStatus::Accepted;
    accepted.accepted_log_sequence = Some(record.log_sequence());
    state.models.insert(id, accepted);
    Ok(())
}

fn model_transition<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
    status: ModelStatus,
) -> Result<(), SemanticError> {
    let id = string(data, "modelId", record)?;
    let model = state.models.get_mut(&id).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::MissingReference,
            record.log_sequence(),
            record.event_kind(),
            "transition references unknown current model",
        )
    })?;
    if !matches!(model.status, ModelStatus::Accepted | ModelStatus::Disputed) {
        return err_for(
            SemanticErrorCode::InvalidLifecycle,
            record,
            "invalid model transition",
        );
    }
    model.status = status;
    if status == ModelStatus::Revoked {
        let model = state.models.remove(&id).expect("checked");
        state.historical_models.insert(id, model);
    }
    Ok(())
}

fn declassification_approved<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "declassificationId", record)?;
    unique(&state.declassifications, &id, record)?;
    let model_id = string(data, "modelId", record)?;
    let model = state.models.get(&model_id).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::MissingReference,
            record.log_sequence(),
            record.event_kind(),
            "declassification model is unknown",
        )
    })?;
    let output = privacy(data, "outputPrivacyClass", record)?;
    let fields = string_set(data, "releasedFields", record)?;
    let policy = string(data, "policyRef", record)?;
    if output >= model.effective_privacy_class
        || fields.is_empty()
        || !fields.iter().all(|field| model.state.contains_key(field))
        || !state.policies.contains(&policy)
    {
        return err_for(
            SemanticErrorCode::DeclassificationInvalid,
            record,
            "declassification must lower privacy, name existing fields, and reference a policy",
        );
    }
    state.declassifications.insert(
        id.clone(),
        Declassification {
            declassification_id: id,
            model_id,
            output_privacy_class: output,
            released_fields: fields,
            policy_ref: policy,
            approved_at_log_sequence: record.log_sequence(),
            revoked_at_log_sequence: None,
        },
    );
    Ok(())
}

fn declassification_revoked<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "declassificationId", record)?;
    let boundary = state.declassifications.get_mut(&id).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::MissingReference,
            record.log_sequence(),
            record.event_kind(),
            "declassification is unknown",
        )
    })?;
    if boundary
        .revoked_at_log_sequence
        .replace(record.log_sequence())
        .is_some()
    {
        return err_for(
            SemanticErrorCode::InvalidLifecycle,
            record,
            "declassification already revoked",
        );
    }
    Ok(())
}

fn contradiction_proposed<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "contradictionId", record)?;
    unique(&state.contradictions, &id, record)?;
    let models = string_set(data, "modelIds", record)?;
    if models.len() < 2 || !models.iter().all(|model| state.models.contains_key(model)) {
        return err_for(
            SemanticErrorCode::MissingReference,
            record,
            "contradiction requires at least two current models",
        );
    }
    state.contradictions.insert(
        id.clone(),
        Contradiction {
            contradiction_id: id,
            model_ids: models,
            status: "PROPOSED".into(),
            proposal_log_sequence: record.log_sequence(),
            review_log_sequence: None,
            resolution: None,
        },
    );
    Ok(())
}

fn contradiction_reviewed<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "contradictionId", record)?;
    let decision = string(data, "decision", record)?;
    if decision != "ACCEPT" && decision != "REJECT" {
        return err_for(
            SemanticErrorCode::InvalidField,
            record,
            "review decision must be ACCEPT or REJECT",
        );
    }
    let contradiction = state.contradictions.get_mut(&id).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::MissingReference,
            record.log_sequence(),
            record.event_kind(),
            "contradiction is unknown",
        )
    })?;
    if contradiction.status != "PROPOSED" {
        return err_for(
            SemanticErrorCode::InvalidLifecycle,
            record,
            "contradiction is not proposed",
        );
    }
    contradiction.status = format!("REVIEWED_{decision}");
    contradiction.review_log_sequence = Some(record.log_sequence());
    Ok(())
}

fn contradiction_accepted<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "contradictionId", record)?;
    let contradiction = state.contradictions.get_mut(&id).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::MissingReference,
            record.log_sequence(),
            record.event_kind(),
            "contradiction is unknown",
        )
    })?;
    if contradiction.status != "REVIEWED_ACCEPT" {
        return err_for(
            SemanticErrorCode::InvalidLifecycle,
            record,
            "contradiction acceptance requires accepted review",
        );
    }
    contradiction.status = "ACCEPTED".into();
    Ok(())
}

fn contradiction_resolved<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "contradictionId", record)?;
    let resolution = data.get("resolution").cloned().ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::InvalidField,
            record.log_sequence(),
            record.event_kind(),
            "resolution is required",
        )
    })?;
    let contradiction = state.contradictions.get_mut(&id).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::MissingReference,
            record.log_sequence(),
            record.event_kind(),
            "contradiction is unknown",
        )
    })?;
    if contradiction.status != "ACCEPTED" {
        return err_for(
            SemanticErrorCode::InvalidLifecycle,
            record,
            "only accepted contradiction can resolve",
        );
    }
    contradiction.status = "RESOLVED".into();
    contradiction.resolution = Some(resolution);
    Ok(())
}

fn topology_added<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "edgeId", record)?;
    unique(&state.topology, &id, record)?;
    let source = string(data, "sourceModelId", record)?;
    let target = string(data, "targetModelId", record)?;
    let edge_type = string(data, "edgeType", record)?;
    let Some(source_model) = state.models.get(&source) else {
        return err_for(
            SemanticErrorCode::MissingReference,
            record,
            "edge source is not current",
        );
    };
    let Some(target_model) = state.models.get(&target) else {
        return err_for(
            SemanticErrorCode::MissingReference,
            record,
            "edge target is not current",
        );
    };
    let declared =
        optional_enum_field(data, "privacyClass", record)?.unwrap_or(PrivacyClass::Public);
    let edge = TopologyEdge {
        edge_id: id.clone(),
        source_model_id: source,
        edge_type,
        target_model_id: target,
        effective_privacy_class: declared
            .max(source_model.effective_privacy_class)
            .max(target_model.effective_privacy_class),
    };
    state.topology.insert(id.clone(), edge);
    if state.topology[&id].edge_type == "DEPENDS_ON" && dependency_cycle(&state.topology) {
        state.topology.remove(&id);
        return err_for(
            SemanticErrorCode::DependencyCycle,
            record,
            "DEPENDS_ON edge creates a cycle",
        );
    }
    Ok(())
}

fn dependency_cycle(edges: &BTreeMap<String, TopologyEdge>) -> bool {
    let mut graph: BTreeMap<&str, BTreeSet<&str>> = BTreeMap::new();
    for edge in edges.values().filter(|edge| edge.edge_type == "DEPENDS_ON") {
        graph
            .entry(&edge.source_model_id)
            .or_default()
            .insert(&edge.target_model_id);
    }
    fn visit<'a>(
        node: &'a str,
        graph: &BTreeMap<&'a str, BTreeSet<&'a str>>,
        visiting: &mut BTreeSet<&'a str>,
        done: &mut BTreeSet<&'a str>,
    ) -> bool {
        if done.contains(node) {
            return false;
        }
        if !visiting.insert(node) {
            return true;
        }
        if graph
            .get(node)
            .is_some_and(|next| next.iter().any(|child| visit(child, graph, visiting, done)))
        {
            return true;
        }
        visiting.remove(node);
        done.insert(node);
        false
    }
    let mut visiting = BTreeSet::new();
    let mut done = BTreeSet::new();
    graph
        .keys()
        .any(|node| visit(node, &graph, &mut visiting, &mut done))
}

fn possible_world_created<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "worldId", record)?;
    if id == ACTUAL_WORLD || state.possible_worlds.contains_key(&id) {
        return err_for(
            SemanticErrorCode::PossibleWorldScopeViolation,
            record,
            "possible world must be unique and distinct from actual world",
        );
    }
    let parent = string(data, "parentWorldId", record)?;
    if parent != ACTUAL_WORLD && !state.possible_worlds.contains_key(&parent) {
        return err_for(
            SemanticErrorCode::MissingReference,
            record,
            "possible-world parent is unknown",
        );
    }
    let mut cursor = parent.as_str();
    while cursor != ACTUAL_WORLD {
        if cursor == id {
            return err_for(
                SemanticErrorCode::PossibleWorldScopeViolation,
                record,
                "possible-world ancestry cycle",
            );
        }
        cursor = state
            .possible_worlds
            .get(cursor)
            .map(|world| world.parent_world_id.as_str())
            .ok_or_else(|| {
                SemanticError::at(
                    SemanticErrorCode::MissingReference,
                    record.log_sequence(),
                    record.event_kind(),
                    "broken possible-world ancestry",
                )
            })?;
    }
    state.possible_worlds.insert(
        id.clone(),
        PossibleWorld {
            world_id: id,
            parent_world_id: parent,
            base_state_id: string(data, "baseStateId", record)?,
            base_time_ns: i64_field(data, "baseTimeNs", record)?,
        },
    );
    Ok(())
}

fn query_authorized<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let authority = parse_authority(data, record)?;
    unique(&state.query_authorities, &authority.authority_id, record)?;
    state
        .query_authorities
        .insert(authority.authority_id.clone(), authority);
    Ok(())
}

fn parse_authority<R: VerifiedRecord>(
    data: &BTreeMap<String, JsonValue>,
    record: &R,
) -> Result<QueryAuthority, SemanticError> {
    let valid_from_ns = i64_field(data, "validFromNs", record)?;
    let valid_to_ns = i64_field(data, "validToNs", record)?;
    if valid_from_ns >= valid_to_ns {
        return err_for(
            SemanticErrorCode::InvalidField,
            record,
            "authority validity interval is empty",
        );
    }
    Ok(QueryAuthority {
        authority_id: string(data, "authorityId", record)?,
        principal_id: string(data, "principalId", record)?,
        recipient_id: string(data, "recipientId", record)?,
        purpose: string(data, "purpose", record)?,
        allowed_subjects: optional_string_set(data, "allowedSubjects", record)?,
        allowed_families: optional_string_set(data, "allowedFamilies", record)?,
        allowed_fields: optional_string_set(data, "allowedFields", record)?,
        world_id: optional_string(data, "worldId", record)?.unwrap_or_else(|| ACTUAL_WORLD.into()),
        max_privacy_class: privacy(data, "maxPrivacyClass", record)?,
        valid_from_ns,
        valid_to_ns,
        revoked_at_log_sequence: None,
    })
}

fn query_authority_revoked<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "authorityId", record)?;
    let authority = state.query_authorities.get_mut(&id).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::MissingReference,
            record.log_sequence(),
            record.event_kind(),
            "authority is unknown",
        )
    })?;
    if authority
        .revoked_at_log_sequence
        .replace(record.log_sequence())
        .is_some()
    {
        return err_for(
            SemanticErrorCode::InvalidLifecycle,
            record,
            "authority already revoked",
        );
    }
    Ok(())
}

fn hpl_requested<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let request = HplRequest {
        request_id: string(data, "requestId", record)?,
        principal_id: string(data, "principalId", record)?,
        recipient_id: string(data, "recipientId", record)?,
        purpose: string(data, "purpose", record)?,
        requested_fields: string_set(data, "requestedFields", record)?,
        max_privacy_class: privacy(data, "maxPrivacyClass", record)?,
        at_ns: i64_field(data, "atNs", record)?,
    };
    unique(&state.hpl_requests, &request.request_id, record)?;
    state
        .hpl_requests
        .insert(request.request_id.clone(), request);
    Ok(())
}

fn hpl_authorized<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let request_id = string(data, "requestId", record)?;
    let request = state.hpl_requests.get(&request_id).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::HplRequestMissing,
            record.log_sequence(),
            record.event_kind(),
            "HPL request is unknown",
        )
    })?;
    let authority = parse_authority(data, record)?;
    if (
        request.principal_id.as_str(),
        request.recipient_id.as_str(),
        request.purpose.as_str(),
    ) != (
        authority.principal_id.as_str(),
        authority.recipient_id.as_str(),
        authority.purpose.as_str(),
    ) || !request
        .requested_fields
        .is_subset(&authority.allowed_fields)
        || request.max_privacy_class > authority.max_privacy_class
    {
        return err_for(
            SemanticErrorCode::AuthorityBindingMismatch,
            record,
            "HPL authority does not exactly cover request binding",
        );
    }
    unique(&state.query_authorities, &authority.authority_id, record)?;
    state
        .query_authorities
        .insert(authority.authority_id.clone(), authority);
    Ok(())
}

fn hpl_issued<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let projection_id = string(data, "projectionId", record)?;
    unique(&state.hpl_projections, &projection_id, record)?;
    let request_id = string(data, "requestId", record)?;
    let authority_id = string(data, "authorityId", record)?;
    let request = state.hpl_requests.get(&request_id).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::HplRequestMissing,
            record.log_sequence(),
            record.event_kind(),
            "HPL request is unknown",
        )
    })?;
    let authority = state.query_authorities.get(&authority_id).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::MissingReference,
            record.log_sequence(),
            record.event_kind(),
            "HPL authority is unknown",
        )
    })?;
    let fields: BTreeMap<_, _> = object(data, "fields", record)?
        .iter()
        .map(|(key, value)| (key.clone(), value.clone()))
        .collect();
    let field_privacy_object = object(data, "fieldPrivacy", record)?;
    let mut field_privacy = BTreeMap::new();
    for (field, value) in field_privacy_object {
        field_privacy.insert(
            field.clone(),
            serde_json::from_value(value.clone()).map_err(|_| {
                SemanticError::at(
                    SemanticErrorCode::PrivacyClassUnknown,
                    record.log_sequence(),
                    record.event_kind(),
                    "unknown field privacy",
                )
            })?,
        );
    }
    let issued_at_ns = i64_field(data, "issuedAtNs", record)?;
    let expires_at_ns = i64_field(data, "expiresAtNs", record)?;
    if authority.revoked_at_log_sequence.is_some() {
        return err_for(
            SemanticErrorCode::AuthorityRevoked,
            record,
            "HPL authority is revoked",
        );
    }
    if issued_at_ns < authority.valid_from_ns
        || issued_at_ns >= authority.valid_to_ns
        || expires_at_ns > authority.valid_to_ns
        || issued_at_ns >= expires_at_ns
    {
        return err_for(
            SemanticErrorCode::AuthorityExpired,
            record,
            "projection is outside authority validity",
        );
    }
    let field_names: BTreeSet<_> = fields.keys().cloned().collect();
    if field_names != field_privacy.keys().cloned().collect()
        || !field_names.is_subset(&request.requested_fields)
        || !field_names.is_subset(&authority.allowed_fields)
        || field_privacy.values().any(|privacy| {
            *privacy > request.max_privacy_class || *privacy > authority.max_privacy_class
        })
    {
        return err_for(
            SemanticErrorCode::AuthorityBindingMismatch,
            record,
            "projection is not least-disclosure within request and authority",
        );
    }
    state.hpl_projections.insert(
        projection_id.clone(),
        HplProjection {
            projection_id,
            request_id,
            authority_id,
            principal_id: request.principal_id.clone(),
            recipient_id: request.recipient_id.clone(),
            purpose: request.purpose.clone(),
            fields,
            field_privacy,
            issued_at_ns,
            expires_at_ns,
            revoked_at_log_sequence: None,
        },
    );
    Ok(())
}

fn hpl_revoked<R: VerifiedRecord>(
    state: &mut SemanticState,
    record: &R,
    data: &BTreeMap<String, JsonValue>,
) -> Result<(), SemanticError> {
    let id = string(data, "projectionId", record)?;
    let projection = state.hpl_projections.get_mut(&id).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::MissingReference,
            record.log_sequence(),
            record.event_kind(),
            "projection is unknown",
        )
    })?;
    if projection
        .revoked_at_log_sequence
        .replace(record.log_sequence())
        .is_some()
    {
        return err_for(
            SemanticErrorCode::InvalidLifecycle,
            record,
            "projection already revoked",
        );
    }
    Ok(())
}

fn execute_query(
    state: &SemanticState,
    query: &SemanticQuery,
) -> Result<QueryResult, SemanticError> {
    let sequence = state.last_log_sequence.unwrap_or(0);
    let kind = "pwm.query.evaluate";
    let authority = state
        .query_authorities
        .get(&query.authority_id)
        .ok_or_else(|| {
            SemanticError::at(
                SemanticErrorCode::AuthorizationMissing,
                sequence,
                kind,
                "query authority is unknown",
            )
        })?;
    if authority.revoked_at_log_sequence.is_some() {
        return err(
            SemanticErrorCode::AuthorityRevoked,
            sequence,
            kind,
            "query authority is revoked",
        );
    }
    if query.at_ns < authority.valid_from_ns || query.at_ns >= authority.valid_to_ns {
        return err(
            SemanticErrorCode::AuthorityExpired,
            sequence,
            kind,
            "query authority is not valid at explicit query time",
        );
    }
    if (
        query.principal_id.as_str(),
        query.recipient_id.as_str(),
        query.purpose.as_str(),
        query.world_id.as_str(),
    ) != (
        authority.principal_id.as_str(),
        authority.recipient_id.as_str(),
        authority.purpose.as_str(),
        authority.world_id.as_str(),
    ) {
        return err(
            SemanticErrorCode::AuthorityBindingMismatch,
            sequence,
            kind,
            "query binding differs from authority",
        );
    }
    if !query.subjects.is_subset(&authority.allowed_subjects)
        || (!authority.allowed_families.is_empty()
            && !query.families.is_subset(&authority.allowed_families))
        || !query.fields.is_subset(&authority.allowed_fields)
        || query.max_privacy_class > authority.max_privacy_class
    {
        return err(
            SemanticErrorCode::QueryUnauthorized,
            sequence,
            kind,
            "query exceeds authorized subjects, families, fields, or privacy",
        );
    }
    let families = if query.families.is_empty() {
        &authority.allowed_families
    } else {
        &query.families
    };
    let mut models = Vec::new();
    for model in state.models.values() {
        if model.world_id != query.world_id
            || (!query.subjects.is_empty() && model.subject_ids.is_disjoint(&query.subjects))
            || !model.subject_ids.is_subset(&authority.allowed_subjects)
            || (!families.is_empty() && !families.contains(&model.family_id))
            || (!query.include_disputed && model.status == ModelStatus::Disputed)
            || !matches!(model.status, ModelStatus::Accepted | ModelStatus::Disputed)
            || model.valid_from_ns.is_some_and(|from| query.at_ns < from)
            || model.valid_to_ns.is_some_and(|to| query.at_ns >= to)
        {
            continue;
        }
        let boundary = state
            .declassifications
            .values()
            .filter(|boundary| {
                boundary.model_id == model.model_id && boundary.revoked_at_log_sequence.is_none()
            })
            .min_by_key(|boundary| (boundary.output_privacy_class, &boundary.declassification_id));
        let (privacy, allowed_fields) =
            boundary.map_or((model.effective_privacy_class, None), |boundary| {
                (
                    boundary.output_privacy_class,
                    Some(&boundary.released_fields),
                )
            });
        if privacy > query.max_privacy_class {
            continue;
        }
        let field_limit = if query.fields.is_empty() {
            &authority.allowed_fields
        } else {
            &query.fields
        };
        let state_fields = model
            .state
            .iter()
            .filter(|(field, _)| {
                (field_limit.is_empty() || field_limit.contains(*field))
                    && allowed_fields.is_none_or(|allowed| allowed.contains(*field))
            })
            .map(|(key, value)| (key.clone(), value.clone()))
            .collect();
        models.push(QueryModel {
            model_id: model.model_id.clone(),
            family_id: model.family_id.clone(),
            kind: model.kind,
            subject_ids: model.subject_ids.clone(),
            state: state_fields,
            status: model.status,
            effective_privacy_class: privacy,
        });
    }
    models.sort_by(|a, b| (&a.family_id, &a.model_id).cmp(&(&b.family_id, &b.model_id)));
    let ids: BTreeSet<_> = models.iter().map(|model| model.model_id.as_str()).collect();
    let edges = state
        .topology
        .values()
        .filter(|edge| {
            ids.contains(edge.source_model_id.as_str())
                && ids.contains(edge.target_model_id.as_str())
                && edge.effective_privacy_class <= query.max_privacy_class
        })
        .cloned()
        .collect();
    let contradictions = state
        .contradictions
        .values()
        .filter(|contradiction| {
            contradiction.status == "ACCEPTED"
                && contradiction
                    .model_ids
                    .iter()
                    .all(|id| ids.contains(id.as_str()))
        })
        .cloned()
        .collect();
    Ok(QueryResult {
        authority_id: query.authority_id.clone(),
        world_id: query.world_id.clone(),
        models,
        edges,
        contradictions,
    })
}

/// CLI-friendly adapter: deserialize owned verified records, reduce, optionally
/// query, and emit compact deterministic JSON (all maps are ordered).
pub fn evaluate(input: EvaluationInput) -> Result<EvaluationOutput, SemanticError> {
    let state = SemanticEngine::reduce(input.records.iter())?;
    let query = input
        .query
        .as_ref()
        .map(|query| execute_query(&state, query))
        .transpose()?;
    Ok(EvaluationOutput { state, query })
}

pub fn evaluate_json(input: &str) -> Result<String, EvaluateJsonError> {
    let request: EvaluationInput = serde_json::from_str(input)?;
    Ok(serde_json::to_string(&evaluate(request)?)?)
}

#[derive(Debug, Error)]
pub enum EvaluateJsonError {
    #[error("invalid evaluation JSON: {0}")]
    Json(#[from] serde_json::Error),
    #[error(transparent)]
    Semantic(#[from] SemanticError),
}

fn privacy<R: VerifiedRecord>(
    data: &BTreeMap<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<PrivacyClass, SemanticError> {
    enum_field(data, field, record, SemanticErrorCode::PrivacyClassUnknown)
}
fn enum_field<T: for<'de> Deserialize<'de>, R: VerifiedRecord>(
    data: &BTreeMap<String, JsonValue>,
    field: &str,
    record: &R,
    code: SemanticErrorCode,
) -> Result<T, SemanticError> {
    serde_json::from_value(data.get(field).cloned().ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::InvalidField,
            record.log_sequence(),
            record.event_kind(),
            format!("missing {field}"),
        )
    })?)
    .map_err(|_| {
        SemanticError::at(
            code,
            record.log_sequence(),
            record.event_kind(),
            format!("invalid {field}"),
        )
    })
}
fn optional_enum_field<T: for<'de> Deserialize<'de>, R: VerifiedRecord>(
    data: &BTreeMap<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<Option<T>, SemanticError> {
    data.get(field)
        .map(|value| {
            serde_json::from_value(value.clone()).map_err(|_| {
                SemanticError::at(
                    SemanticErrorCode::PrivacyClassUnknown,
                    record.log_sequence(),
                    record.event_kind(),
                    format!("invalid {field}"),
                )
            })
        })
        .transpose()
}
fn string<R: VerifiedRecord, M: MapLookup>(
    data: &M,
    field: &str,
    record: &R,
) -> Result<String, SemanticError> {
    let value = data
        .lookup(field)
        .and_then(JsonValue::as_str)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| {
            SemanticError::at(
                SemanticErrorCode::InvalidField,
                record.log_sequence(),
                record.event_kind(),
                format!("{field} must be non-empty text"),
            )
        })?;
    Ok(value.into())
}
fn optional_string<R: VerifiedRecord, M: MapLookup>(
    data: &M,
    field: &str,
    record: &R,
) -> Result<Option<String>, SemanticError> {
    match data.lookup(field) {
        None | Some(JsonValue::Null) => Ok(None),
        Some(JsonValue::String(value)) if !value.is_empty() => Ok(Some(value.clone())),
        _ => err_for(
            SemanticErrorCode::InvalidField,
            record,
            format!("{field} must be text or null"),
        ),
    }
}
fn array<'a, R: VerifiedRecord>(
    data: &'a BTreeMap<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<&'a Vec<JsonValue>, SemanticError> {
    data.get(field)
        .and_then(JsonValue::as_array)
        .ok_or_else(|| {
            SemanticError::at(
                SemanticErrorCode::InvalidField,
                record.log_sequence(),
                record.event_kind(),
                format!("{field} must be an array"),
            )
        })
}
fn object<'a, R: VerifiedRecord>(
    data: &'a BTreeMap<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<&'a Map<String, JsonValue>, SemanticError> {
    data.get(field)
        .and_then(JsonValue::as_object)
        .ok_or_else(|| {
            SemanticError::at(
                SemanticErrorCode::InvalidField,
                record.log_sequence(),
                record.event_kind(),
                format!("{field} must be a map"),
            )
        })
}
fn object_value<'a, R: VerifiedRecord>(
    value: &'a JsonValue,
    name: &str,
    record: &R,
) -> Result<&'a Map<String, JsonValue>, SemanticError> {
    value.as_object().ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::InvalidField,
            record.log_sequence(),
            record.event_kind(),
            format!("{name} must be a map"),
        )
    })
}
fn optional_object<R: VerifiedRecord>(
    data: &BTreeMap<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<BTreeMap<String, JsonValue>, SemanticError> {
    match data.get(field) {
        None => Ok(BTreeMap::new()),
        Some(JsonValue::Object(value)) => Ok(value
            .iter()
            .map(|(key, value)| (key.clone(), value.clone()))
            .collect()),
        _ => err_for(
            SemanticErrorCode::InvalidField,
            record,
            format!("{field} must be a map"),
        ),
    }
}
fn string_set<R: VerifiedRecord, M: MapLookup>(
    data: &M,
    field: &str,
    record: &R,
) -> Result<BTreeSet<String>, SemanticError> {
    let values = data
        .lookup(field)
        .and_then(JsonValue::as_array)
        .ok_or_else(|| {
            SemanticError::at(
                SemanticErrorCode::InvalidField,
                record.log_sequence(),
                record.event_kind(),
                format!("{field} must be an array"),
            )
        })?;
    let mut result = BTreeSet::new();
    for value in values {
        let Some(value) = value.as_str().filter(|value| !value.is_empty()) else {
            return err_for(
                SemanticErrorCode::InvalidField,
                record,
                format!("{field} values must be non-empty text"),
            );
        };
        if !result.insert(value.into()) {
            return err_for(
                SemanticErrorCode::InvalidField,
                record,
                format!("{field} values must be unique"),
            );
        }
    }
    Ok(result)
}
fn optional_string_set<R: VerifiedRecord, M: MapLookup>(
    data: &M,
    field: &str,
    record: &R,
) -> Result<BTreeSet<String>, SemanticError> {
    if data.lookup(field).is_some() {
        string_set(data, field, record)
    } else {
        Ok(BTreeSet::new())
    }
}
trait MapLookup {
    fn lookup(&self, key: &str) -> Option<&JsonValue>;
}
impl MapLookup for BTreeMap<String, JsonValue> {
    fn lookup(&self, key: &str) -> Option<&JsonValue> {
        self.get(key)
    }
}
impl MapLookup for Map<String, JsonValue> {
    fn lookup(&self, key: &str) -> Option<&JsonValue> {
        self.get(key)
    }
}
fn optional_u64_field<R: VerifiedRecord, M: MapLookup>(
    data: &M,
    field: &str,
    record: &R,
) -> Result<Option<u64>, SemanticError> {
    match data.lookup(field) {
        None | Some(JsonValue::Null) => Ok(None),
        Some(value) => value.as_u64().map(Some).ok_or_else(|| {
            SemanticError::at(
                SemanticErrorCode::InvalidField,
                record.log_sequence(),
                record.event_kind(),
                format!("{field} must be unsigned or null"),
            )
        }),
    }
}
fn i64_field<R: VerifiedRecord>(
    data: &BTreeMap<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<i64, SemanticError> {
    data.get(field).and_then(JsonValue::as_i64).ok_or_else(|| {
        SemanticError::at(
            SemanticErrorCode::InvalidField,
            record.log_sequence(),
            record.event_kind(),
            format!("{field} must be an integer"),
        )
    })
}
fn unique<V, R: VerifiedRecord>(
    map: &BTreeMap<String, V>,
    id: &str,
    record: &R,
) -> Result<(), SemanticError> {
    if map.contains_key(id) {
        err_for(
            SemanticErrorCode::DuplicateId,
            record,
            format!("duplicate id: {id}"),
        )
    } else {
        Ok(())
    }
}
fn err<T>(
    code: SemanticErrorCode,
    sequence: u64,
    kind: &str,
    message: impl Into<String>,
) -> Result<T, SemanticError> {
    Err(SemanticError::at(code, sequence, kind, message))
}
fn err_for<T, R: VerifiedRecord>(
    code: SemanticErrorCode,
    record: &R,
    message: impl Into<String>,
) -> Result<T, SemanticError> {
    err(code, record.log_sequence(), record.event_kind(), message)
}
