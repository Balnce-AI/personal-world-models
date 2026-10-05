use std::collections::{BTreeMap, BTreeSet};

use pwm_canonical::{Value, decode_canonical, encode};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value as JsonValue, json};
use sha2::{Digest, Sha256};

use crate::{
    ACTUAL_WORLD, OwnedVerifiedRecord, SEMANTIC_PROFILE, SEMANTIC_SCHEMA_VERSION, SemanticError,
    SemanticErrorCode, VerifiedRecord,
};

pub const IMPLEMENTATION_ID: &str = "pwm-semantic-rust";

const PRIVACY: [&str; 5] = ["PUBLIC", "LOW", "PERSONAL", "SENSITIVE", "HIGHLY_SENSITIVE"];

const REGISTRY: [(&str, &str, &str); 22] = [
    ("pwm.evidence", "EVIDENCE_CREATE", "pwm.evidence.write"),
    ("pwm.policy", "POLICY_CREATE", "pwm.policy.write"),
    ("pwm.model.propose", "MODEL_PROPOSE", "pwm.model.propose"),
    ("pwm.model.review", "MODEL_REVIEW", "pwm.model.review"),
    ("pwm.model.accept", "MODEL_ACCEPT", "pwm.model.accept"),
    ("pwm.model.update", "MODEL_UPDATE", "pwm.model.update"),
    ("pwm.model.dispute", "MODEL_DISPUTE", "pwm.model.dispute"),
    ("pwm.model.revoke", "MODEL_REVOKE", "pwm.model.revoke"),
    (
        "pwm.privacy-boundary.approve",
        "PRIVACY_BOUNDARY_APPROVE",
        "pwm.privacy-boundary.approve",
    ),
    (
        "pwm.privacy-boundary.revoke",
        "PRIVACY_BOUNDARY_REVOKE",
        "pwm.privacy-boundary.revoke",
    ),
    (
        "pwm.contradiction.propose",
        "CONTRADICTION_PROPOSE",
        "pwm.contradiction.propose",
    ),
    (
        "pwm.contradiction.review",
        "CONTRADICTION_REVIEW",
        "pwm.contradiction.review",
    ),
    (
        "pwm.contradiction.accept",
        "CONTRADICTION_ACCEPT",
        "pwm.contradiction.accept",
    ),
    (
        "pwm.contradiction.resolve",
        "CONTRADICTION_RESOLVE",
        "pwm.contradiction.resolve",
    ),
    (
        "pwm.topology.edge",
        "TOPOLOGY_EDGE_CREATE",
        "pwm.topology.edge",
    ),
    (
        "pwm.possible-world",
        "POSSIBLE_WORLD_CREATE",
        "pwm.possible-world.create",
    ),
    (
        "pwm.query-authority",
        "QUERY_AUTHORITY_GRANT",
        "pwm.query-authority.grant",
    ),
    ("hpl.request", "HPL_REQUEST_CREATE", "hpl.request.create"),
    (
        "hpl.authorization",
        "HPL_AUTHORIZE",
        "hpl.authorization.create",
    ),
    ("hpl.projection", "HPL_PROJECT", "hpl.projection.create"),
    ("hpl.revoke", "HPL_REVOKE", "hpl.revoke"),
    (
        "pwm.conformance.evaluate",
        "CONFORMANCE_EVALUATE",
        "pwm.conformance.evaluate",
    ),
];

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct Implementation {
    pub id: String,
    pub version: String,
    pub adapter_version: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SignedQuery {
    pub authority_id: String,
    pub world_id: String,
    pub as_of_valid_ns: i64,
    pub recipient_id: String,
    pub purpose: String,
    pub model_ids: Vec<String>,
    pub include_disputed: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ConformanceCommand {
    pub operation: String,
    pub evaluation_log_sequence: u64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub query: Option<SignedQuery>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub projection_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub evaluation_id: Option<String>,
}

/// Adapter input for records already authenticated by `pwm-event`.
///
/// `OwnedVerifiedRecord` is only a transport shape. Production callers should
/// call `ConformanceEngine::apply` with `pwm_event::VerifiedRecordRef` values.
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ConformanceInput {
    pub source_id: String,
    pub records: Vec<OwnedVerifiedRecord>,
    pub command: ConformanceCommand,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct ConformanceResult {
    pub operation: String,
    pub state_sha256: String,
    pub value: JsonValue,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct ConformanceFailure {
    pub code: SemanticErrorCode,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub at_event_body_cid: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct ConformanceOutput {
    pub output_version: String,
    pub profile: String,
    pub source_id: String,
    pub implementation: Implementation,
    pub decision: String,
    pub processed_records: usize,
    pub last_committed_log_sequence: Option<u64>,
    pub state_sha256: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<ConformanceResult>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<ConformanceFailure>,
}

#[derive(Clone, Debug, Default)]
struct State {
    accepted_event_ids: Vec<String>,
    event_types: BTreeMap<String, String>,
    principals: BTreeMap<String, JsonValue>,
    grants: BTreeMap<String, JsonValue>,
    families: BTreeMap<String, JsonValue>,
    evidence: BTreeMap<String, JsonValue>,
    policies: BTreeMap<String, JsonValue>,
    candidates: BTreeMap<String, JsonValue>,
    proposal_events: BTreeMap<String, String>,
    reviews: BTreeMap<String, JsonValue>,
    review_events: BTreeMap<String, String>,
    models: BTreeMap<String, JsonValue>,
    privacy_boundaries: BTreeMap<String, JsonValue>,
    contradiction_candidates: BTreeMap<String, JsonValue>,
    contradiction_proposals: BTreeMap<String, String>,
    contradiction_reviews: BTreeMap<String, JsonValue>,
    contradiction_review_events: BTreeMap<String, String>,
    contradictions: BTreeMap<String, JsonValue>,
    edges: BTreeMap<String, JsonValue>,
    worlds: BTreeMap<String, JsonValue>,
    query_authorities: BTreeMap<String, JsonValue>,
    hpl_requests: BTreeMap<String, JsonValue>,
    hpl_authorizations: BTreeMap<String, JsonValue>,
    projections: BTreeMap<String, JsonValue>,
    evaluations: BTreeMap<String, JsonValue>,
    last_sequence: Option<u64>,
}

#[derive(Clone, Debug, Default)]
pub struct ConformanceEngine {
    state: State,
}

struct Envelope {
    data: Map<String, JsonValue>,
    valid_from_ns: i64,
    valid_to_ns: Option<i64>,
}

impl ConformanceEngine {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn processed_records(&self) -> usize {
        self.state.accepted_event_ids.len()
    }

    pub fn last_committed_log_sequence(&self) -> Option<u64> {
        self.state.last_sequence
    }

    pub fn state_value(&self) -> JsonValue {
        state_value(&self.state)
    }

    /// Atomically applies one cryptographically verified record.
    pub fn apply<R: VerifiedRecord>(&mut self, record: &R) -> Result<(), SemanticError> {
        let sequence = record.log_sequence();
        let kind = record.event_kind();
        if sequence != self.state.last_sequence.map_or(0, |value| value + 1) {
            return fail(
                SemanticErrorCode::ReceiptInvalid,
                record,
                "non-contiguous receipt sequence",
            );
        }
        if kind != "pwm.genesis" && registry(kind).is_none() {
            return fail(
                SemanticErrorCode::UnsupportedEventKind,
                record,
                "unregistered event kind",
            );
        }
        if record.schema_version() != SEMANTIC_SCHEMA_VERSION {
            return fail(
                SemanticErrorCode::UnsupportedSchemaVersion,
                record,
                "unsupported event schema",
            );
        }
        let envelope = envelope(record)?;
        let event_id = record
            .event_body_cid()
            .unwrap_or_else(|| format!("fixture:{sequence}"));
        if self.state.event_types.contains_key(&event_id) {
            return fail(
                SemanticErrorCode::IdentifierConflict,
                record,
                "duplicate event CID",
            );
        }
        if record
            .parent_event_cids()
            .iter()
            .any(|parent| !self.state.event_types.contains_key(parent))
        {
            return fail(
                SemanticErrorCode::ParentInvalid,
                record,
                "parent is not committed",
            );
        }
        let mut next = self.state.clone();
        if kind == "pwm.genesis" {
            genesis(&mut next, record, &envelope.data)?;
        } else {
            let principal = authenticate(&next, record)?;
            apply_event(&mut next, record, &event_id, &principal, &envelope)?;
        }
        next.accepted_event_ids.push(event_id.clone());
        next.event_types.insert(event_id, kind.to_owned());
        next.last_sequence = Some(sequence);
        self.state = next;
        Ok(())
    }

    pub fn command(&self, command: &ConformanceCommand) -> Result<JsonValue, SemanticError> {
        if self.state.last_sequence.is_none()
            || command.evaluation_log_sequence > self.state.last_sequence.unwrap_or_default()
        {
            return command_fail(
                SemanticErrorCode::ReceiptInvalid,
                "unknown evaluation frontier",
            );
        }
        match command.operation.as_str() {
            "REDUCE"
                if command.query.is_none()
                    && command.projection_id.is_none()
                    && command.evaluation_id.is_none() =>
            {
                Ok(self.state_value())
            }
            "QUERY" if command.projection_id.is_none() && command.evaluation_id.is_none() => query(
                &self.state,
                command.query.as_ref().ok_or_else(command_shape)?,
                command.evaluation_log_sequence,
            ),
            "PROJECT" if command.query.is_none() && command.evaluation_id.is_none() => self
                .state
                .projections
                .get(command.projection_id.as_deref().ok_or_else(command_shape)?)
                .cloned()
                .ok_or_else(|| {
                    command_error(SemanticErrorCode::ReferenceNotFound, "projection not found")
                }),
            "EVALUATE" if command.query.is_none() && command.projection_id.is_none() => self
                .state
                .evaluations
                .get(command.evaluation_id.as_deref().ok_or_else(command_shape)?)
                .cloned()
                .ok_or_else(|| {
                    command_error(SemanticErrorCode::ReferenceNotFound, "evaluation not found")
                }),
            _ => command_fail(
                SemanticErrorCode::CommandUnsupported,
                "invalid command shape or operation",
            ),
        }
    }
}

pub fn evaluate_conformance(input: ConformanceInput) -> ConformanceOutput {
    evaluate_verified(input.source_id, &input.records, input.command)
}

pub(crate) fn evaluate_verified<R: VerifiedRecord>(
    source_id: String,
    records: &[R],
    command: ConformanceCommand,
) -> ConformanceOutput {
    let mut engine = ConformanceEngine::new();
    for record in records {
        if record.log_sequence() > command.evaluation_log_sequence {
            continue;
        }
        if let Err(error) = engine.apply(record) {
            return output(
                source_id,
                &engine,
                "REJECT",
                None,
                Some(ConformanceFailure {
                    code: stable_code(error.code),
                    at_event_body_cid: record.event_body_cid(),
                }),
            );
        }
    }
    match engine.command(&command) {
        Ok(value) => output(
            source_id,
            &engine,
            "ACCEPT",
            Some(ConformanceResult {
                operation: command.operation,
                state_sha256: state_digest(&engine.state_value()),
                value,
            }),
            None,
        ),
        Err(error) => output(
            source_id,
            &engine,
            "REJECT",
            None,
            Some(ConformanceFailure {
                code: stable_code(error.code),
                at_event_body_cid: None,
            }),
        ),
    }
}

pub(crate) fn rejected_output(
    source_id: String,
    code: SemanticErrorCode,
    at_event_body_cid: Option<String>,
) -> ConformanceOutput {
    output(
        source_id,
        &ConformanceEngine::new(),
        "REJECT",
        None,
        Some(ConformanceFailure {
            code,
            at_event_body_cid,
        }),
    )
}

pub fn evaluate_conformance_json(input: &str) -> Result<String, serde_json::Error> {
    let input: ConformanceInput = serde_json::from_str(input)?;
    serde_json::to_string(&evaluate_conformance(input))
}

pub fn identify() -> JsonValue {
    json!({
        "implementation": IMPLEMENTATION_ID,
        "profiles": ["pwm-public-provenance-v1", SEMANTIC_PROFILE],
        "protocolVersion": SEMANTIC_SCHEMA_VERSION
    })
}

fn output(
    source_id: String,
    engine: &ConformanceEngine,
    decision: &str,
    result: Option<ConformanceResult>,
    error: Option<ConformanceFailure>,
) -> ConformanceOutput {
    ConformanceOutput {
        output_version: SEMANTIC_SCHEMA_VERSION.into(),
        profile: SEMANTIC_PROFILE.into(),
        source_id,
        implementation: Implementation {
            id: IMPLEMENTATION_ID.into(),
            version: env!("CARGO_PKG_VERSION").into(),
            adapter_version: SEMANTIC_SCHEMA_VERSION.into(),
        },
        decision: decision.into(),
        processed_records: engine.processed_records(),
        last_committed_log_sequence: engine.last_committed_log_sequence(),
        state_sha256: state_digest(&engine.state_value()),
        result,
        error,
    }
}

fn registry(kind: &str) -> Option<(&'static str, &'static str)> {
    REGISTRY
        .iter()
        .find(|entry| entry.0 == kind)
        .map(|entry| (entry.1, entry.2))
}

fn envelope<R: VerifiedRecord>(record: &R) -> Result<Envelope, SemanticError> {
    let value = decode_canonical(record.payload_cbor()).map_err(|error| {
        SemanticError::at(
            if error == pwm_canonical::CanonicalError::NonCanonical {
                SemanticErrorCode::CborNonCanonical
            } else {
                SemanticErrorCode::CborInvalid
            },
            record.log_sequence(),
            record.event_kind(),
            error.to_string(),
        )
    })?;
    let Value::Map(entries) = value else {
        return fail(
            SemanticErrorCode::PayloadEnvelopeInvalid,
            record,
            "envelope must be a map",
        );
    };
    let fields: BTreeMap<_, _> = entries.into_iter().collect();
    exact_keys(
        &fields,
        &[
            "profile",
            "schema_version",
            "data",
            "valid_from_ns",
            "valid_to_ns",
        ],
        record,
        SemanticErrorCode::PayloadEnvelopeInvalid,
    )?;
    if fields.get("profile") != Some(&Value::Text(SEMANTIC_PROFILE.into())) {
        return fail(
            SemanticErrorCode::PayloadEnvelopeInvalid,
            record,
            "wrong payload profile",
        );
    }
    if fields.get("schema_version") != Some(&Value::Text(SEMANTIC_SCHEMA_VERSION.into())) {
        return fail(
            SemanticErrorCode::UnsupportedSchemaVersion,
            record,
            "wrong payload schema",
        );
    }
    let Value::Map(data) = &fields["data"] else {
        return fail(
            SemanticErrorCode::PayloadEnvelopeInvalid,
            record,
            "data must be a map",
        );
    };
    let valid_from_ns = integer(&fields["valid_from_ns"])
        .ok_or_else(|| field_error(record, "valid_from_ns must be an integer"))?;
    let valid_to_ns = match &fields["valid_to_ns"] {
        Value::Null => None,
        value => Some(
            integer(value)
                .ok_or_else(|| field_error(record, "valid_to_ns must be null or integer"))?,
        ),
    };
    if valid_to_ns.is_some_and(|end| end <= valid_from_ns) {
        return fail(
            SemanticErrorCode::PayloadEnvelopeInvalid,
            record,
            "invalid validity interval",
        );
    }
    Ok(Envelope {
        data: data
            .iter()
            .map(|(key, value)| (key.clone(), value_json(value)))
            .collect(),
        valid_from_ns,
        valid_to_ns,
    })
}

fn genesis<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "scope_id",
            "root_principal_id",
            "root_key_id",
            "principals",
            "grants",
        ],
        record,
    )?;
    if record.log_sequence() != 0
        || !state.accepted_event_ids.is_empty()
        || text(data, "scope_id", record)? != record.principal_scope()
        || text(data, "root_key_id", record)? != record.author_key_id()
    {
        return fail(
            SemanticErrorCode::RootTrustMismatch,
            record,
            "invalid genesis trust binding",
        );
    }
    for principal in canonical_objects(data, "principals", record)? {
        exact(principal, &["principal_id", "principal_class"], record)?;
        let id = text(principal, "principal_id", record)?;
        if state
            .principals
            .insert(id, JsonValue::Object(principal.clone()))
            .is_some()
        {
            return fail(
                SemanticErrorCode::IdentifierConflict,
                record,
                "duplicate principal",
            );
        }
    }
    for grant in canonical_objects(data, "grants", record)? {
        exact(
            grant,
            &[
                "grant_id",
                "principal_id",
                "key_id",
                "scope_id",
                "operations",
                "capabilities",
                "grant_class",
                "valid_from_log_sequence",
                "valid_to_log_sequence",
            ],
            record,
        )?;
        canonical_texts(grant, "operations", record, false)?;
        canonical_texts(grant, "capabilities", record, false)?;
        let id = text(grant, "grant_id", record)?;
        let principal = text(grant, "principal_id", record)?;
        let start = unsigned(grant, "valid_from_log_sequence", record)?;
        let end = optional_unsigned(grant, "valid_to_log_sequence", record)?;
        if !state.principals.contains_key(&principal)
            || text(grant, "scope_id", record)? != record.principal_scope()
            || end.is_some_and(|value| value <= start)
        {
            return fail(
                SemanticErrorCode::PayloadFieldInvalid,
                record,
                "invalid genesis grant",
            );
        }
        if state
            .grants
            .insert(id, JsonValue::Object(grant.clone()))
            .is_some()
        {
            return fail(
                SemanticErrorCode::IdentifierConflict,
                record,
                "duplicate grant",
            );
        }
    }
    let root_principal = text(data, "root_principal_id", record)?;
    let root = state.grants.values().any(|grant| {
        grant["grant_class"] == "ROOT"
            && grant["principal_id"] == root_principal
            && grant["key_id"] == record.author_key_id()
            && grant["valid_from_log_sequence"] == 0
    });
    if !root {
        return fail(
            SemanticErrorCode::RootTrustMismatch,
            record,
            "root grant missing",
        );
    }
    state.worlds.insert(
        ACTUAL_WORLD.into(),
        json!({"worldId": ACTUAL_WORLD, "parentWorldId": null}),
    );
    for (family, kinds, minimum) in [
        ("pwm.preference", &["SELF", "OTHER"][..], 1),
        ("pwm.relationship", &["RELATIONSHIP"][..], 2),
        ("pwm.physical-environment", &["WORLD"][..], 1),
        (
            "pwm.imagination-possible-worlds",
            &["POSSIBLE_WORLD"][..],
            1,
        ),
        ("pwm.models-of-models", &["META"][..], 1),
        ("fc.meta", &["META"][..], 1),
    ] {
        state.families.insert(
            family.into(),
            json!({"allowedKinds": kinds, "minSubjects": minimum, "maxSubjects": null}),
        );
    }
    Ok(())
}

fn authenticate<R: VerifiedRecord>(state: &State, record: &R) -> Result<String, SemanticError> {
    let (operation, capability) = registry(record.event_kind()).expect("registry checked");
    let matching: Vec<_> = state
        .grants
        .values()
        .filter(|grant| {
            grant["key_id"] == record.author_key_id()
                && grant["scope_id"] == record.principal_scope()
                && grant["operations"]
                    .as_array()
                    .is_some_and(|items| items.iter().any(|item| item == operation || item == "*"))
        })
        .collect();
    if matching.is_empty() {
        return fail(
            SemanticErrorCode::GrantNotFound,
            record,
            "operation grant not found",
        );
    }
    let active: Vec<_> = matching
        .into_iter()
        .filter(|grant| {
            grant["valid_from_log_sequence"]
                .as_u64()
                .is_some_and(|start| start <= record.log_sequence())
                && (grant["valid_to_log_sequence"].is_null()
                    || grant["valid_to_log_sequence"]
                        .as_u64()
                        .is_some_and(|end| record.log_sequence() < end))
        })
        .collect();
    if active.is_empty() {
        return fail(
            SemanticErrorCode::GrantNotActive,
            record,
            "grant is inactive",
        );
    }
    let principals: BTreeSet<_> = active
        .iter()
        .filter_map(|grant| grant["principal_id"].as_str())
        .collect();
    if principals.len() != 1 {
        return fail(
            SemanticErrorCode::PrincipalAmbiguous,
            record,
            "active grants disagree on principal",
        );
    }
    if !active.iter().any(|grant| {
        grant["capabilities"]
            .as_array()
            .is_some_and(|items| items.iter().any(|item| item == capability || item == "*"))
    }) {
        return fail(
            SemanticErrorCode::CapabilityNotGranted,
            record,
            "required capability not granted",
        );
    }
    Ok((*principals.iter().next().expect("one principal")).into())
}

fn apply_event<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    event_id: &str,
    principal: &str,
    envelope: &Envelope,
) -> Result<(), SemanticError> {
    let data = &envelope.data;
    match record.event_kind() {
        "pwm.evidence" => evidence(state, record, data),
        "pwm.policy" => policy(state, record, data),
        "pwm.model.propose" => model_propose(state, record, data, principal),
        "pwm.model.review" => model_review(state, record, data, principal),
        "pwm.model.accept" => model_accept(state, record, data, envelope, false),
        "pwm.model.update" => model_accept(state, record, data, envelope, true),
        "pwm.model.dispute" | "pwm.model.revoke" => model_transition(state, record, data),
        "pwm.privacy-boundary.approve" => boundary_approve(state, record, data, principal),
        "pwm.privacy-boundary.revoke" => boundary_revoke(state, record, data),
        "pwm.contradiction.propose" => contradiction_propose(state, record, data, principal),
        "pwm.contradiction.review" => contradiction_review(state, record, data, principal),
        "pwm.contradiction.accept" => contradiction_accept(state, record, data),
        "pwm.contradiction.resolve" => contradiction_resolve(state, record, data, principal),
        "pwm.topology.edge" => topology(state, record, data),
        "pwm.possible-world" => possible_world(state, record, data),
        "pwm.query-authority" => query_authority(state, record, data, principal),
        "hpl.request" => hpl_request(state, record, data, principal),
        "hpl.authorization" => hpl_authorization(state, record, data, principal),
        "hpl.projection" => hpl_projection(state, record, data),
        "hpl.revoke" => hpl_revoke(state, record, data),
        "pwm.conformance.evaluate" => evaluation(state, record, data),
        _ => fail(
            SemanticErrorCode::UnsupportedEventKind,
            record,
            "unregistered event kind",
        ),
    }?;
    // The event ID is retained separately from payload IDs for provenance.
    let _ = event_id;
    Ok(())
}

fn evidence<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "evidence_id",
            "evidence_kind",
            "subject_ids",
            "source_uri",
            "content_digest",
            "privacy_class",
            "properties",
        ],
        record,
    )?;
    canonical_texts(data, "subject_ids", record, true)?;
    privacy(data, "privacy_class", record)?;
    bytes_len(data, "content_digest", 32, record)?;
    object(data, "properties", record)?;
    let id = text(data, "evidence_id", record)?;
    let mut value = data.clone();
    value.insert("evidenceId".into(), id.clone().into());
    value.insert("privacyClass".into(), data["privacy_class"].clone());
    value.insert(
        "effectivePrivacyClass".into(),
        data["privacy_class"].clone(),
    );
    insert(&mut state.evidence, id, JsonValue::Object(value), record)
}

fn policy<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "policy_id",
            "policy_profile",
            "content_digest",
            "privacy_floor",
            "properties",
        ],
        record,
    )?;
    bytes_len(data, "content_digest", 32, record)?;
    privacy(data, "privacy_floor", record)?;
    object(data, "properties", record)?;
    let id = text(data, "policy_id", record)?;
    insert(
        &mut state.policies,
        id,
        JsonValue::Object(data.clone()),
        record,
    )
}

fn model_propose<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
    principal: &str,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "proposal_id",
            "model_id",
            "family",
            "kind",
            "subject_ids",
            "perspective_id",
            "world_id",
            "evidence_ids",
            "declared_privacy_class",
            "properties",
            "confidence",
        ],
        record,
    )?;
    let proposal_id = text(data, "proposal_id", record)?;
    let model_id = text(data, "model_id", record)?;
    if state.candidates.contains_key(&model_id)
        || state.models.contains_key(&model_id)
        || state.proposal_events.values().any(|id| id == &proposal_id)
    {
        return fail(
            SemanticErrorCode::IdentifierConflict,
            record,
            "model or proposal already exists",
        );
    }
    let subjects = canonical_texts(data, "subject_ids", record, true)?;
    let evidence_ids = canonical_texts(data, "evidence_ids", record, false)?;
    if evidence_ids
        .iter()
        .any(|id| !state.evidence.contains_key(id))
    {
        return fail(
            SemanticErrorCode::ReferenceNotFound,
            record,
            "evidence not found",
        );
    }
    let kind = text(data, "kind", record)?;
    let family_id = text(data, "family", record)?;
    let family = state.families.get(&family_id).ok_or_else(|| {
        semantic(
            record,
            SemanticErrorCode::FamilyKindNotAllowed,
            "unknown model family",
        )
    })?;
    if !family["allowedKinds"]
        .as_array()
        .is_some_and(|items| items.contains(&JsonValue::String(kind.clone())))
        || subjects.len() < family["minSubjects"].as_u64().unwrap_or(1) as usize
    {
        return fail(
            SemanticErrorCode::FamilyKindNotAllowed,
            record,
            "model violates family constraints",
        );
    }
    let world = text(data, "world_id", record)?;
    let perspective = optional_text(data, "perspective_id", record)?;
    if !matches!(
        kind.as_str(),
        "SELF" | "OTHER" | "RELATIONSHIP" | "WORLD" | "META" | "POSSIBLE_WORLD"
    ) || (kind == "RELATIONSHIP" && subjects.len() < 2)
        || (kind == "SELF" && (subjects.len() != 1 || subjects[0] != principal))
    {
        return fail(
            SemanticErrorCode::FamilyKindNotAllowed,
            record,
            "model kind/cardinality violation",
        );
    }
    if kind == "POSSIBLE_WORLD" {
        if world == ACTUAL_WORLD || !state.worlds.contains_key(&world) {
            return fail(
                SemanticErrorCode::WorldScopeViolation,
                record,
                "possible-world model has invalid world",
            );
        }
    } else if !state.worlds.contains_key(&world) {
        return fail(
            SemanticErrorCode::WorldScopeViolation,
            record,
            "model world not found",
        );
    }
    fixed_confidence(data.get("confidence"), record)?;
    let declared = privacy(data, "declared_privacy_class", record)?;
    let effective = evidence_ids.iter().try_fold(declared, |current, id| {
        let value = state.evidence[id]["privacy_class"]
            .as_str()
            .ok_or_else(|| field_error(record, "invalid evidence privacy"))?;
        Ok::<_, SemanticError>(max_privacy(current, value))
    })?;
    let mut model = Map::new();
    model.insert("modelId".into(), model_id.clone().into());
    model.insert("familyId".into(), family_id.into());
    model.insert("kind".into(), kind.into());
    model.insert("subjectIds".into(), data["subject_ids"].clone());
    model.insert(
        "perspective".into(),
        perspective.map_or(JsonValue::Null, JsonValue::String),
    );
    model.insert("worldId".into(), world.into());
    model.insert("evidenceRefs".into(), data["evidence_ids"].clone());
    model.insert("privacyClass".into(), declared.into());
    model.insert("effectivePrivacyClass".into(), effective.into());
    model.insert("state".into(), data["properties"].clone());
    model.insert("confidence".into(), data["confidence"].clone());
    model.insert("_authorPrincipal".into(), principal.into());
    state.proposal_events.insert(model_id.clone(), proposal_id);
    state.candidates.insert(model_id, JsonValue::Object(model));
    Ok(())
}

fn model_review<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
    principal: &str,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "review_id",
            "proposal_id",
            "reviewer_principal_id",
            "decision",
            "reason",
        ],
        record,
    )?;
    let proposal = text(data, "proposal_id", record)?;
    let model_id = state
        .proposal_events
        .iter()
        .find_map(|(model, id)| (id == &proposal).then(|| model.clone()))
        .ok_or_else(|| {
            semantic(
                record,
                SemanticErrorCode::ReferenceNotFound,
                "proposal not found",
            )
        })?;
    let reviewer = text(data, "reviewer_principal_id", record)?;
    if reviewer != principal {
        return fail(
            SemanticErrorCode::AuthorityScopeViolation,
            record,
            "reviewer is not authenticated principal",
        );
    }
    let decision = text(data, "decision", record)?;
    if !matches!(decision.as_str(), "APPROVE" | "REJECT") {
        return fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            "invalid review decision",
        );
    }
    if state.candidates[&model_id]["_authorPrincipal"] == principal
        && !principal_has_capability(
            state,
            principal,
            record.author_key_id(),
            "pwm.review.self",
            record.log_sequence(),
        )
    {
        return fail(
            SemanticErrorCode::ReviewSeparationViolation,
            record,
            "self-review is not granted",
        );
    }
    let review_id = text(data, "review_id", record)?;
    if state.review_events.values().any(|id| id == &review_id) {
        return fail(
            SemanticErrorCode::IdentifierConflict,
            record,
            "review already exists",
        );
    }
    state.review_events.insert(model_id.clone(), review_id);
    state
        .reviews
        .insert(model_id, JsonValue::Object(data.clone()));
    Ok(())
}

fn model_accept<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
    envelope: &Envelope,
    update: bool,
) -> Result<(), SemanticError> {
    let fields = if update {
        &["model_id", "previous_model_id", "proposal_id", "review_id"][..]
    } else {
        &["model_id", "proposal_id", "review_id"][..]
    };
    exact(data, fields, record)?;
    let id = text(data, "model_id", record)?;
    let candidate = state.candidates.get(&id).cloned().ok_or_else(|| {
        semantic(
            record,
            SemanticErrorCode::LifecyclePreconditionMissing,
            "candidate not found",
        )
    })?;
    let review = state.reviews.get(&id).ok_or_else(|| {
        semantic(
            record,
            SemanticErrorCode::LifecyclePreconditionMissing,
            "review not found",
        )
    })?;
    if text(data, "proposal_id", record)? != state.proposal_events[&id]
        || text(data, "review_id", record)? != state.review_events[&id]
        || review["decision"] != "APPROVE"
    {
        return fail(
            SemanticErrorCode::LifecyclePreconditionMissing,
            record,
            "proposal/review chain does not approve candidate",
        );
    }
    if state.models.contains_key(&id) {
        return fail(
            SemanticErrorCode::IdentifierConflict,
            record,
            "model already materialized",
        );
    }
    if update {
        let previous = text(data, "previous_model_id", record)?;
        let predecessor = state.models.get(&previous).ok_or_else(|| {
            semantic(
                record,
                SemanticErrorCode::LifecyclePreconditionMissing,
                "current predecessor not found",
            )
        })?;
        if previous == id
            || !matches!(
                predecessor["lifecycleStatus"].as_str(),
                Some("ACCEPTED" | "DISPUTED")
            )
            || ["familyId", "kind", "subjectIds", "perspective", "worldId"]
                .iter()
                .any(|field| candidate[*field] != predecessor[*field])
        {
            return fail(
                SemanticErrorCode::LifecyclePreconditionMissing,
                record,
                "invalid predecessor",
            );
        }
        state
            .models
            .get_mut(&previous)
            .and_then(JsonValue::as_object_mut)
            .expect("model object")
            .insert("lifecycleStatus".into(), "SUPERSEDED".into());
    }
    let mut accepted = candidate.as_object().expect("candidate object").clone();
    accepted.remove("_authorPrincipal");
    accepted.insert("lifecycleStatus".into(), "ACCEPTED".into());
    accepted.insert("proposalEventId".into(), data["proposal_id"].clone());
    accepted.insert("reviewEventId".into(), data["review_id"].clone());
    accepted.insert("validFrom".into(), envelope.valid_from_ns.into());
    accepted.insert(
        "validTo".into(),
        envelope
            .valid_to_ns
            .map_or(JsonValue::Null, JsonValue::from),
    );
    state.models.insert(id.clone(), JsonValue::Object(accepted));
    state.candidates.remove(&id);
    state.reviews.remove(&id);
    Ok(())
}

fn model_transition<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
) -> Result<(), SemanticError> {
    let dispute = record.event_kind().ends_with("dispute");
    exact(
        data,
        if dispute {
            &["model_id", "reason", "evidence_ids"]
        } else {
            &["model_id", "reason"]
        },
        record,
    )?;
    if dispute {
        canonical_texts(data, "evidence_ids", record, false)?;
    }
    let id = text(data, "model_id", record)?;
    let model = state.models.get_mut(&id).ok_or_else(|| {
        semantic(
            record,
            SemanticErrorCode::ReferenceNotFound,
            "model not found",
        )
    })?;
    let status = model["lifecycleStatus"].as_str();
    if (dispute && status != Some("ACCEPTED"))
        || (!dispute && !matches!(status, Some("ACCEPTED" | "DISPUTED")))
    {
        return fail(
            SemanticErrorCode::LifecyclePreconditionMissing,
            record,
            "invalid model transition",
        );
    }
    model.as_object_mut().expect("model object").insert(
        "lifecycleStatus".into(),
        if dispute { "DISPUTED" } else { "REVOKED" }.into(),
    );
    Ok(())
}

fn boundary_approve<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
    principal: &str,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "boundary_id",
            "boundary_kind",
            "policy_id",
            "source_ids",
            "input_privacy_class",
            "output_privacy_class",
            "released_fields",
            "approver_principal_id",
            "expires_at_log_sequence",
        ],
        record,
    )?;
    let sources = canonical_texts(data, "source_ids", record, true)?;
    canonical_texts(data, "released_fields", record, true)?;
    if text(data, "approver_principal_id", record)? != principal {
        return fail(
            SemanticErrorCode::AuthorityScopeViolation,
            record,
            "approver mismatch",
        );
    }
    if !matches!(
        text(data, "boundary_kind", record)?.as_str(),
        "REDACTION" | "PROOF"
    ) {
        return fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            "invalid boundary kind",
        );
    }
    if sources.iter().any(|id| !has_reference(state, id))
        || !has_reference(state, &text(data, "policy_id", record)?)
    {
        return fail(
            SemanticErrorCode::ReferenceNotFound,
            record,
            "boundary source or policy not found",
        );
    }
    let input = privacy(data, "input_privacy_class", record)?;
    let output = privacy(data, "output_privacy_class", record)?;
    if privacy_rank(output) > privacy_rank(input) {
        return fail(
            SemanticErrorCode::PrivacyEffectiveClassMismatch,
            record,
            "boundary raises privacy",
        );
    }
    let mut value = data.clone();
    value.insert("status".into(), "ACTIVE".into());
    insert(
        &mut state.privacy_boundaries,
        text(data, "boundary_id", record)?,
        JsonValue::Object(value),
        record,
    )
}

fn boundary_revoke<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
) -> Result<(), SemanticError> {
    exact(data, &["boundary_id", "reason"], record)?;
    let id = text(data, "boundary_id", record)?;
    let boundary = state.privacy_boundaries.get_mut(&id).ok_or_else(|| {
        semantic(
            record,
            SemanticErrorCode::ReferenceNotFound,
            "boundary not found",
        )
    })?;
    if boundary["status"] != "ACTIVE" {
        return fail(
            SemanticErrorCode::LifecyclePreconditionMissing,
            record,
            "boundary inactive",
        );
    }
    boundary
        .as_object_mut()
        .expect("object")
        .insert("status".into(), "REVOKED".into());
    Ok(())
}

fn contradiction_propose<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
    principal: &str,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "proposal_id",
            "contradiction_id",
            "contradiction_type",
            "reference_ids",
            "world_id",
            "evidence_ids",
            "explanation",
        ],
        record,
    )?;
    let references = canonical_texts(data, "reference_ids", record, true)?;
    canonical_texts(data, "evidence_ids", record, false)?;
    if references.len() < 2 || references.iter().any(|id| !has_reference(state, id)) {
        return fail(
            SemanticErrorCode::ReferenceNotFound,
            record,
            "contradiction inputs not found",
        );
    }
    let id = text(data, "contradiction_id", record)?;
    if state.contradictions.contains_key(&id) || state.contradiction_candidates.contains_key(&id) {
        return fail(
            SemanticErrorCode::IdentifierConflict,
            record,
            "contradiction exists",
        );
    }
    state
        .contradiction_proposals
        .insert(id.clone(), text(data, "proposal_id", record)?);
    let mut candidate = Map::new();
    candidate.insert("contradictionId".into(), id.clone().into());
    candidate.insert("status".into(), "OPEN".into());
    candidate.insert("modelIds".into(), data["reference_ids"].clone());
    candidate.insert("evidenceIds".into(), data["evidence_ids"].clone());
    candidate.insert("worldId".into(), data["world_id"].clone());
    candidate.insert(
        "contradictionType".into(),
        data["contradiction_type"].clone(),
    );
    candidate.insert("explanation".into(), data["explanation"].clone());
    candidate.insert("_authorPrincipal".into(), principal.into());
    state
        .contradiction_candidates
        .insert(id, JsonValue::Object(candidate));
    Ok(())
}

fn contradiction_review<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
    principal: &str,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "review_id",
            "proposal_id",
            "reviewer_principal_id",
            "decision",
            "reason",
        ],
        record,
    )?;
    if text(data, "reviewer_principal_id", record)? != principal {
        return fail(
            SemanticErrorCode::AuthorityScopeViolation,
            record,
            "reviewer mismatch",
        );
    }
    let proposal = text(data, "proposal_id", record)?;
    let id = state
        .contradiction_proposals
        .iter()
        .find_map(|(id, value)| (value == &proposal).then(|| id.clone()))
        .ok_or_else(|| {
            semantic(
                record,
                SemanticErrorCode::ReferenceNotFound,
                "proposal not found",
            )
        })?;
    if !matches!(
        text(data, "decision", record)?.as_str(),
        "APPROVE" | "REJECT"
    ) {
        return fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            "invalid decision",
        );
    }
    if state.contradiction_candidates[&id]["_authorPrincipal"] == principal
        && !principal_has_capability(
            state,
            principal,
            record.author_key_id(),
            "pwm.review.self",
            record.log_sequence(),
        )
    {
        return fail(
            SemanticErrorCode::ReviewSeparationViolation,
            record,
            "self-review is not granted",
        );
    }
    state
        .contradiction_review_events
        .insert(id.clone(), text(data, "review_id", record)?);
    state
        .contradiction_reviews
        .insert(id, JsonValue::Object(data.clone()));
    Ok(())
}

fn contradiction_accept<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
) -> Result<(), SemanticError> {
    exact(
        data,
        &["contradiction_id", "proposal_id", "review_id"],
        record,
    )?;
    let id = text(data, "contradiction_id", record)?;
    let candidate = state
        .contradiction_candidates
        .get(&id)
        .cloned()
        .ok_or_else(|| {
            semantic(
                record,
                SemanticErrorCode::LifecyclePreconditionMissing,
                "candidate missing",
            )
        })?;
    let review = state.contradiction_reviews.get(&id).ok_or_else(|| {
        semantic(
            record,
            SemanticErrorCode::LifecyclePreconditionMissing,
            "review missing",
        )
    })?;
    if state.contradiction_proposals.get(&id) != Some(&text(data, "proposal_id", record)?)
        || state.contradiction_review_events.get(&id) != Some(&text(data, "review_id", record)?)
        || review["decision"] != "APPROVE"
    {
        return fail(
            SemanticErrorCode::LifecyclePreconditionMissing,
            record,
            "contradiction chain invalid",
        );
    }
    let mut value = candidate.as_object().expect("object").clone();
    value.remove("_authorPrincipal");
    value.insert("status".into(), "OPEN".into());
    value.insert("resolutions".into(), json!([]));
    state.contradiction_candidates.remove(&id);
    state.contradictions.insert(id, JsonValue::Object(value));
    Ok(())
}

fn contradiction_resolve<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
    principal: &str,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "resolution_id",
            "contradiction_id",
            "status",
            "resolver_principal_id",
            "explanation",
            "evidence_ids",
        ],
        record,
    )?;
    if text(data, "resolver_principal_id", record)? != principal {
        return fail(
            SemanticErrorCode::AuthorityScopeViolation,
            record,
            "resolver mismatch",
        );
    }
    if !matches!(
        text(data, "status", record)?.as_str(),
        "EXPLAINED" | "SUPERSEDED" | "RESOLVED" | "IRREDUCIBLE" | "PERSPECTIVE_DEPENDENT"
    ) {
        return fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            "invalid resolution",
        );
    }
    let evidence = canonical_texts(data, "evidence_ids", record, false)?;
    if evidence.iter().any(|id| !state.evidence.contains_key(id)) {
        return fail(
            SemanticErrorCode::ReferenceNotFound,
            record,
            "resolution evidence missing",
        );
    }
    let id = text(data, "contradiction_id", record)?;
    let contradiction = state.contradictions.get_mut(&id).ok_or_else(|| {
        semantic(
            record,
            SemanticErrorCode::ReferenceNotFound,
            "contradiction missing",
        )
    })?;
    let object = contradiction.as_object_mut().expect("object");
    object.insert("status".into(), data["status"].clone());
    let resolution = json!({
        "contradictionId": data["contradiction_id"],
        "status": data["status"],
        "resolver": data["resolver_principal_id"],
        "evidenceRefs": data["evidence_ids"],
        "resolutionId": data["resolution_id"],
        "explanation": data["explanation"]
    });
    object
        .get_mut("resolutions")
        .and_then(JsonValue::as_array_mut)
        .expect("array")
        .push(resolution);
    Ok(())
}

fn topology<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "edge_id",
            "source_model_id",
            "target_model_id",
            "edge_type",
            "world_id",
            "evidence_ids",
            "declared_privacy_class",
        ],
        record,
    )?;
    let source = text(data, "source_model_id", record)?;
    let target = text(data, "target_model_id", record)?;
    if source == target
        || !state.models.contains_key(&source)
        || !state.models.contains_key(&target)
    {
        return fail(
            SemanticErrorCode::ReferenceNotFound,
            record,
            "edge endpoint missing",
        );
    }
    let world = text(data, "world_id", record)?;
    if state.models[&source]["worldId"] != world || state.models[&target]["worldId"] != world {
        return fail(
            SemanticErrorCode::WorldScopeViolation,
            record,
            "edge crosses worlds",
        );
    }
    canonical_texts(data, "evidence_ids", record, false)?;
    let declared = privacy(data, "declared_privacy_class", record)?;
    let id = text(data, "edge_id", record)?;
    let effective = max_privacy(
        declared,
        max_privacy(
            state.models[&source]["effectivePrivacyClass"]
                .as_str()
                .expect("validated model privacy"),
            state.models[&target]["effectivePrivacyClass"]
                .as_str()
                .expect("validated model privacy"),
        ),
    );
    let mut edge = Map::new();
    edge.insert("edgeId".into(), id.clone().into());
    edge.insert("sourceModelId".into(), source.into());
    edge.insert("targetModelId".into(), target.into());
    edge.insert("edgeType".into(), data["edge_type"].clone());
    edge.insert("worldId".into(), world.into());
    edge.insert("evidenceIds".into(), data["evidence_ids"].clone());
    edge.insert("privacyClass".into(), declared.into());
    edge.insert("effectivePrivacyClass".into(), effective.into());
    insert(
        &mut state.edges,
        id.clone(),
        JsonValue::Object(edge),
        record,
    )?;
    if data["edge_type"] == "DEPENDS_ON" && topology_cycle(&state.edges) {
        state.edges.remove(&id);
        return fail(SemanticErrorCode::TopologyCycle, record, "dependency cycle");
    }
    Ok(())
}

fn possible_world<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "world_id",
            "parent_world_id",
            "base_state_cid",
            "base_time_ns",
            "declared_privacy_class",
            "purpose",
        ],
        record,
    )?;
    let id = text(data, "world_id", record)?;
    let parent = text(data, "parent_world_id", record)?;
    if id == ACTUAL_WORLD || id == parent || state.worlds.contains_key(&id) {
        return fail(
            SemanticErrorCode::IdentifierConflict,
            record,
            "invalid world ID",
        );
    }
    if !state.worlds.contains_key(&parent) {
        return fail(
            SemanticErrorCode::ReferenceNotFound,
            record,
            "parent world missing",
        );
    }
    bytes_len(data, "base_state_cid", 32, record)?;
    privacy(data, "declared_privacy_class", record)?;
    state.worlds.insert(id, JsonValue::Object(data.clone()));
    Ok(())
}

fn query_authority<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
    principal: &str,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "authority_id",
            "principal_id",
            "recipient_id",
            "purpose",
            "world_ids",
            "subject_ids",
            "perspective_ids",
            "families",
            "privacy_ceiling",
            "allow_disputed",
            "valid_from_log_sequence",
            "valid_to_log_sequence",
        ],
        record,
    )?;
    for field in ["world_ids", "subject_ids", "perspective_ids", "families"] {
        canonical_texts(data, field, record, field == "world_ids")?;
    }
    if text(data, "principal_id", record)? != principal {
        return fail(
            SemanticErrorCode::AuthorityScopeViolation,
            record,
            "authority principal mismatch",
        );
    }
    if array(data, "world_ids", record)?.iter().any(|world| {
        !world
            .as_str()
            .is_some_and(|id| state.worlds.contains_key(id))
    }) {
        return fail(
            SemanticErrorCode::WorldScopeViolation,
            record,
            "authority world missing",
        );
    }
    privacy(data, "privacy_ceiling", record)?;
    interval(data, record)?;
    insert(
        &mut state.query_authorities,
        text(data, "authority_id", record)?,
        JsonValue::Object(data.clone()),
        record,
    )
}

fn hpl_request<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
    principal: &str,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "request_id",
            "requester_principal_id",
            "recipient_id",
            "purpose",
            "world_id",
            "model_ids",
            "requested_fields",
            "maximum_privacy_class",
            "retention_until_ns",
            "capabilities",
        ],
        record,
    )?;
    for field in ["model_ids", "requested_fields", "capabilities"] {
        canonical_texts(data, field, record, field == "model_ids")?;
    }
    if text(data, "requester_principal_id", record)? != principal {
        return fail(
            SemanticErrorCode::AuthorityScopeViolation,
            record,
            "requester mismatch",
        );
    }
    if !state.worlds.contains_key(&text(data, "world_id", record)?)
        || array(data, "model_ids", record)?
            .iter()
            .any(|id| !id.as_str().is_some_and(|id| state.models.contains_key(id)))
    {
        return fail(
            SemanticErrorCode::ReferenceNotFound,
            record,
            "request world/model missing",
        );
    }
    privacy(data, "maximum_privacy_class", record)?;
    insert(
        &mut state.hpl_requests,
        text(data, "request_id", record)?,
        JsonValue::Object(data.clone()),
        record,
    )
}

fn hpl_authorization<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
    principal: &str,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "authorization_id",
            "request_id",
            "query_authority_id",
            "authorizer_principal_id",
            "allowed_model_ids",
            "allowed_fields",
            "privacy_ceiling",
            "valid_to_log_sequence",
        ],
        record,
    )?;
    let request_id = text(data, "request_id", record)?;
    let authority_id = text(data, "query_authority_id", record)?;
    let request = state.hpl_requests.get(&request_id).ok_or_else(|| {
        semantic(
            record,
            SemanticErrorCode::ReferenceNotFound,
            "request missing",
        )
    })?;
    let authority = state.query_authorities.get(&authority_id).ok_or_else(|| {
        semantic(
            record,
            SemanticErrorCode::ReferenceNotFound,
            "authority missing",
        )
    })?;
    if text(data, "authorizer_principal_id", record)? != principal {
        return fail(
            SemanticErrorCode::AuthorityScopeViolation,
            record,
            "authorizer mismatch",
        );
    }
    let models = canonical_texts(data, "allowed_model_ids", record, false)?;
    let fields = canonical_texts(data, "allowed_fields", record, false)?;
    if !subset(&models, &request["model_ids"])
        || request["recipient_id"] != authority["recipient_id"]
        || request["purpose"] != authority["purpose"]
        || !authority["world_ids"]
            .as_array()
            .is_some_and(|items| items.contains(&request["world_id"]))
        || privacy_rank(privacy(data, "privacy_ceiling", record)?)
            > privacy_rank(authority["privacy_ceiling"].as_str().unwrap_or("PUBLIC"))
        || fields.iter().any(|field| field.is_empty())
    {
        return fail(
            SemanticErrorCode::AuthorityScopeViolation,
            record,
            "authorization exceeds request/authority",
        );
    }
    let mut value = data.clone();
    value.insert("status".into(), "ACTIVE".into());
    insert(
        &mut state.hpl_authorizations,
        text(data, "authorization_id", record)?,
        JsonValue::Object(value),
        record,
    )
}

fn hpl_projection<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "projection_id",
            "authorization_id",
            "recipient_id",
            "purpose",
            "world_id",
            "model_ids",
            "released_fields",
            "effective_privacy_class",
            "boundary_ids",
            "content_digest",
            "expires_at_ns",
        ],
        record,
    )?;
    let authorization = state
        .hpl_authorizations
        .get(&text(data, "authorization_id", record)?)
        .ok_or_else(|| {
            semantic(
                record,
                SemanticErrorCode::ReferenceNotFound,
                "authorization missing",
            )
        })?;
    if authorization["status"] != "ACTIVE"
        || record.log_sequence() >= authorization["valid_to_log_sequence"].as_u64().unwrap_or(0)
    {
        return fail(
            SemanticErrorCode::AuthorityExpired,
            record,
            "authorization inactive",
        );
    }
    let request = &state.hpl_requests[authorization["request_id"].as_str().expect("request id")];
    let models = canonical_texts(data, "model_ids", record, true)?;
    let fields = canonical_texts(data, "released_fields", record, true)?;
    let boundaries = canonical_texts(data, "boundary_ids", record, false)?;
    if data["recipient_id"] != request["recipient_id"]
        || data["purpose"] != request["purpose"]
        || data["world_id"] != request["world_id"]
        || !subset(&models, &authorization["allowed_model_ids"])
        || !subset(&fields, &authorization["allowed_fields"])
    {
        return fail(
            SemanticErrorCode::AuthorityScopeViolation,
            record,
            "projection binding exceeds authorization",
        );
    }
    let mut effective = "PUBLIC";
    for model in &models {
        let Some(value) = state.models.get(model) else {
            return fail(
                SemanticErrorCode::ReferenceNotFound,
                record,
                "projection model missing",
            );
        };
        effective = max_privacy(
            effective,
            value["effectivePrivacyClass"].as_str().unwrap_or("PUBLIC"),
        );
    }
    for id in boundaries {
        let Some(boundary) = state.privacy_boundaries.get(&id) else {
            return fail(
                SemanticErrorCode::ReferenceNotFound,
                record,
                "boundary missing",
            );
        };
        if boundary["status"] != "ACTIVE" {
            return fail(
                SemanticErrorCode::ReferenceNotFound,
                record,
                "boundary inactive",
            );
        }
        if subset(&models, &boundary["source_ids"]) && subset(&fields, &boundary["released_fields"])
        {
            let output = boundary["output_privacy_class"]
                .as_str()
                .unwrap_or(effective);
            if privacy_rank(output) < privacy_rank(effective) {
                effective = output;
            }
        }
    }
    if privacy(data, "effective_privacy_class", record)? != effective {
        return fail(
            SemanticErrorCode::PrivacyEffectiveClassMismatch,
            record,
            "projection privacy mismatch",
        );
    }
    bytes_len(data, "content_digest", 32, record)?;
    let mut value = data.clone();
    value.insert("status".into(), "ACTIVE".into());
    insert(
        &mut state.projections,
        text(data, "projection_id", record)?,
        JsonValue::Object(value),
        record,
    )
}

fn hpl_revoke<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
) -> Result<(), SemanticError> {
    exact(data, &["target_type", "target_id", "reason"], record)?;
    let id = text(data, "target_id", record)?;
    let target = match text(data, "target_type", record)?.as_str() {
        "AUTHORIZATION" => state.hpl_authorizations.get_mut(&id),
        "PROJECTION" => state.projections.get_mut(&id),
        _ => {
            return fail(
                SemanticErrorCode::PayloadFieldInvalid,
                record,
                "invalid HPL target type",
            );
        }
    }
    .ok_or_else(|| {
        semantic(
            record,
            SemanticErrorCode::ReferenceNotFound,
            "HPL target missing",
        )
    })?;
    if target["status"] != "ACTIVE" {
        return fail(
            SemanticErrorCode::LifecyclePreconditionMissing,
            record,
            "HPL target inactive",
        );
    }
    let object = target.as_object_mut().expect("object");
    object.insert("status".into(), "REVOKED".into());
    object.insert(
        "revoked_at_log_sequence".into(),
        record.log_sequence().into(),
    );
    Ok(())
}

fn evaluation<R: VerifiedRecord>(
    state: &mut State,
    record: &R,
    data: &Map<String, JsonValue>,
) -> Result<(), SemanticError> {
    exact(
        data,
        &[
            "evaluation_id",
            "suite_id",
            "suite_version",
            "suite_sha256",
            "implementation_id",
            "implementation_version",
            "passed_case_ids",
            "failed_case_ids",
            "evaluated_at_ns",
        ],
        record,
    )?;
    bytes_len(data, "suite_sha256", 32, record)?;
    let passed = canonical_texts(data, "passed_case_ids", record, false)?;
    let failed = canonical_texts(data, "failed_case_ids", record, false)?;
    if passed.iter().any(|id| failed.contains(id)) {
        return fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            "case sets overlap",
        );
    }
    insert(
        &mut state.evaluations,
        text(data, "evaluation_id", record)?,
        JsonValue::Object(data.clone()),
        record,
    )
}

fn query(state: &State, query: &SignedQuery, sequence: u64) -> Result<JsonValue, SemanticError> {
    let authority = state
        .query_authorities
        .get(&query.authority_id)
        .ok_or_else(|| {
            command_error(SemanticErrorCode::ReferenceNotFound, "authority not found")
        })?;
    let start = authority["valid_from_log_sequence"]
        .as_u64()
        .unwrap_or(u64::MAX);
    let end = authority["valid_to_log_sequence"].as_u64();
    if sequence < start || end.is_some_and(|end| sequence >= end) {
        return command_fail(SemanticErrorCode::AuthorityExpired, "authority expired");
    }
    if authority["recipient_id"] != query.recipient_id
        || authority["purpose"] != query.purpose
        || !authority["world_ids"]
            .as_array()
            .is_some_and(|items| items.contains(&JsonValue::String(query.world_id.clone())))
    {
        return command_fail(
            SemanticErrorCode::AuthorityScopeViolation,
            "query binding mismatch",
        );
    }
    let mut requested = query.model_ids.clone();
    requested.sort_by(|left, right| left.as_bytes().cmp(right.as_bytes()));
    if requested.windows(2).any(|pair| pair[0] == pair[1]) {
        return command_fail(SemanticErrorCode::PayloadFieldInvalid, "duplicate model ID");
    }
    let mut selected = Vec::new();
    for id in requested {
        let model = state.models.get(&id).ok_or_else(|| {
            command_error(SemanticErrorCode::ReferenceNotFound, "model not found")
        })?;
        if model["worldId"] != query.world_id {
            return command_fail(
                SemanticErrorCode::WorldScopeViolation,
                "model world mismatch",
            );
        }
        let status = model["lifecycleStatus"].as_str();
        if status == Some("DISPUTED")
            && !(query.include_disputed && authority["allow_disputed"] == true)
        {
            continue;
        }
        if !matches!(status, Some("ACCEPTED" | "DISPUTED")) {
            continue;
        }
        if !subset_json(&model["subjectIds"], &authority["subject_ids"])
            || !authority["families"]
                .as_array()
                .is_some_and(|items| items.contains(&model["familyId"]))
            || !authority["perspective_ids"]
                .as_array()
                .is_some_and(|items| items.contains(&model["perspective"]))
            || privacy_rank(model["effectivePrivacyClass"].as_str().unwrap_or("PUBLIC"))
                > privacy_rank(authority["privacy_ceiling"].as_str().unwrap_or("PUBLIC"))
        {
            return command_fail(
                SemanticErrorCode::AuthorityScopeViolation,
                "model exceeds authority",
            );
        }
        if model["validFrom"]
            .as_i64()
            .is_some_and(|from| query.as_of_valid_ns < from)
            || model["validTo"]
                .as_i64()
                .is_some_and(|to| query.as_of_valid_ns >= to)
        {
            continue;
        }
        selected.push(id);
    }
    let set: BTreeSet<_> = selected.iter().cloned().collect();
    let edges: Vec<_> = state
        .edges
        .iter()
        .filter(|(_, edge)| {
            edge["sourceModelId"]
                .as_str()
                .is_some_and(|id| set.contains(id))
                && edge["targetModelId"]
                    .as_str()
                    .is_some_and(|id| set.contains(id))
        })
        .map(|(id, _)| id.clone())
        .collect();
    Ok(json!({"model_ids": selected, "edge_ids": edges}))
}

fn state_value(state: &State) -> JsonValue {
    let current: Vec<_> = state
        .models
        .iter()
        .filter(|(_, model)| {
            matches!(
                model["lifecycleStatus"].as_str(),
                Some("ACCEPTED" | "DISPUTED")
            )
        })
        .map(|(id, _)| id.clone())
        .collect();
    let historical: Vec<_> = state
        .models
        .iter()
        .filter(|(_, model)| {
            !matches!(
                model["lifecycleStatus"].as_str(),
                Some("ACCEPTED" | "DISPUTED")
            )
        })
        .map(|(id, _)| id.clone())
        .collect();
    let worlds: BTreeMap<_, _> = state
        .worlds
        .keys()
        .map(|world| {
            (
                world.clone(),
                JsonValue::Array(
                    state
                        .models
                        .iter()
                        .filter(|(_, model)| model["worldId"] == *world)
                        .map(|(id, _)| id.clone().into())
                        .collect(),
                ),
            )
        })
        .collect();
    json!({
        "acceptedEventIds": state.accepted_event_ids,
        "principals": state.principals,
        "families": state.families,
        "grants": state.grants,
        "evidence": state.evidence,
        "policies": state.policies,
        "models": state.models,
        "currentModelIds": current,
        "historicalModelIds": historical,
        "candidateModelIds": state.candidates.keys().collect::<Vec<_>>(),
        "derivedModels": {},
        "edges": state.edges,
        "possibleWorlds": worlds,
        "contradictions": state.contradictions,
        "contradictionCandidateIds": state.contradiction_candidates.keys().collect::<Vec<_>>(),
        "predictions": {}, "calibrations": {},
        "queryAuthorities": state.query_authorities,
        "projections": state.projections,
        "projectionRevocations": {},
        "privacyBoundaries": state.privacy_boundaries,
        "hplRequests": state.hpl_requests,
        "hplAuthorizations": state.hpl_authorizations,
        "evaluations": state.evaluations,
        "query": null
    })
}

fn state_digest(state: &JsonValue) -> String {
    let mut hasher = Sha256::new();
    hasher.update(b"pwm:semantic-state:v1\0");
    hasher.update(encode(&json_cbor(state)).expect("state is restricted CBOR"));
    hex_string(&hasher.finalize())
}

fn value_json(value: &Value) -> JsonValue {
    match value {
        Value::Null => JsonValue::Null,
        Value::Bool(value) => (*value).into(),
        Value::Unsigned(value) => (*value).into(),
        Value::Negative(value) => (*value).into(),
        Value::Bytes(value) => json!({"$bytes_hex": hex_string(value)}),
        Value::Text(value) => value.clone().into(),
        Value::Array(values) => values.iter().map(value_json).collect(),
        Value::Map(values) => values
            .iter()
            .map(|(key, value)| (key.clone(), value_json(value)))
            .collect(),
    }
}

fn json_cbor(value: &JsonValue) -> Value {
    match value {
        JsonValue::Null => Value::Null,
        JsonValue::Bool(value) => Value::Bool(*value),
        JsonValue::Number(value) => value.as_u64().map_or_else(
            || Value::Negative(value.as_i64().expect("integer")),
            Value::Unsigned,
        ),
        JsonValue::String(value) => Value::Text(value.clone()),
        JsonValue::Array(values) => Value::Array(values.iter().map(json_cbor).collect()),
        JsonValue::Object(values) if values.len() == 1 && values.contains_key("$bytes_hex") => {
            Value::Bytes(
                hex_bytes(values["$bytes_hex"].as_str().expect("hex")).expect("valid stored hex"),
            )
        }
        JsonValue::Object(values) => Value::Map(
            values
                .iter()
                .map(|(key, value)| (key.clone(), json_cbor(value)))
                .collect(),
        ),
    }
}

fn exact<R: VerifiedRecord>(
    data: &Map<String, JsonValue>,
    fields: &[&str],
    record: &R,
) -> Result<(), SemanticError> {
    let actual: BTreeSet<_> = data.keys().map(String::as_str).collect();
    let expected: BTreeSet<_> = fields.iter().copied().collect();
    if actual == expected {
        Ok(())
    } else {
        fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            "payload fields are not exact",
        )
    }
}
fn exact_keys<R: VerifiedRecord>(
    data: &BTreeMap<String, Value>,
    fields: &[&str],
    record: &R,
    code: SemanticErrorCode,
) -> Result<(), SemanticError> {
    let actual: BTreeSet<_> = data.keys().map(String::as_str).collect();
    let expected: BTreeSet<_> = fields.iter().copied().collect();
    if actual == expected {
        Ok(())
    } else {
        fail(code, record, "map fields are not exact")
    }
}
fn text<R: VerifiedRecord>(
    data: &Map<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<String, SemanticError> {
    data.get(field)
        .and_then(JsonValue::as_str)
        .filter(|value| !value.is_empty() && value.len() <= 256)
        .map(str::to_owned)
        .ok_or_else(|| field_error(record, format!("{field} must be bounded non-empty text")))
}
fn optional_text<R: VerifiedRecord>(
    data: &Map<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<Option<String>, SemanticError> {
    match data.get(field) {
        Some(JsonValue::Null) => Ok(None),
        Some(JsonValue::String(value)) if !value.is_empty() && value.len() <= 256 => {
            Ok(Some(value.clone()))
        }
        _ => fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            format!("{field} must be text or null"),
        ),
    }
}
fn array<'a, R: VerifiedRecord>(
    data: &'a Map<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<&'a Vec<JsonValue>, SemanticError> {
    data.get(field)
        .and_then(JsonValue::as_array)
        .ok_or_else(|| field_error(record, format!("{field} must be an array")))
}
fn object<'a, R: VerifiedRecord>(
    data: &'a Map<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<&'a Map<String, JsonValue>, SemanticError> {
    data.get(field)
        .and_then(JsonValue::as_object)
        .ok_or_else(|| field_error(record, format!("{field} must be a map")))
}
fn canonical_texts<R: VerifiedRecord>(
    data: &Map<String, JsonValue>,
    field: &str,
    record: &R,
    nonempty: bool,
) -> Result<Vec<String>, SemanticError> {
    let items = array(data, field, record)?;
    let result: Vec<_> = items
        .iter()
        .map(|value| {
            value
                .as_str()
                .filter(|value| !value.is_empty() && value.len() <= 256)
                .map(str::to_owned)
                .ok_or_else(|| field_error(record, format!("{field} contains invalid text")))
        })
        .collect::<Result<_, _>>()?;
    let encoded: Vec<_> = items
        .iter()
        .map(|item| encode(&json_cbor(item)).expect("restricted"))
        .collect();
    if (nonempty && result.is_empty()) || encoded.windows(2).any(|pair| pair[0] >= pair[1]) {
        return fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            format!("{field} is not a canonical set"),
        );
    }
    Ok(result)
}
fn canonical_objects<'a, R: VerifiedRecord>(
    data: &'a Map<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<Vec<&'a Map<String, JsonValue>>, SemanticError> {
    let items = array(data, field, record)?;
    if items.is_empty() {
        return fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            format!("{field} is empty"),
        );
    }
    let encoded: Vec<_> = items
        .iter()
        .map(|item| encode(&json_cbor(item)).expect("restricted"))
        .collect();
    if encoded.windows(2).any(|pair| pair[0] >= pair[1]) {
        return fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            format!("{field} is not canonical"),
        );
    }
    items
        .iter()
        .map(|value| {
            value
                .as_object()
                .ok_or_else(|| field_error(record, format!("{field} item must be a map")))
        })
        .collect()
}
fn unsigned<R: VerifiedRecord>(
    data: &Map<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<u64, SemanticError> {
    data.get(field)
        .and_then(JsonValue::as_u64)
        .ok_or_else(|| field_error(record, format!("{field} must be unsigned")))
}
fn optional_unsigned<R: VerifiedRecord>(
    data: &Map<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<Option<u64>, SemanticError> {
    match data.get(field) {
        Some(JsonValue::Null) => Ok(None),
        Some(value) => value
            .as_u64()
            .map(Some)
            .ok_or_else(|| field_error(record, format!("{field} must be unsigned or null"))),
        None => Err(field_error(record, format!("{field} missing"))),
    }
}
fn interval<R: VerifiedRecord>(
    data: &Map<String, JsonValue>,
    record: &R,
) -> Result<(), SemanticError> {
    let start = unsigned(data, "valid_from_log_sequence", record)?;
    if optional_unsigned(data, "valid_to_log_sequence", record)?.is_some_and(|end| end <= start) {
        fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            "invalid sequence interval",
        )
    } else {
        Ok(())
    }
}
fn privacy<'a, R: VerifiedRecord>(
    data: &'a Map<String, JsonValue>,
    field: &str,
    record: &R,
) -> Result<&'a str, SemanticError> {
    let value = data
        .get(field)
        .and_then(JsonValue::as_str)
        .ok_or_else(|| field_error(record, format!("{field} missing")))?;
    if PRIVACY.contains(&value) {
        Ok(value)
    } else {
        fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            "unknown privacy class",
        )
    }
}
fn privacy_rank(value: &str) -> usize {
    PRIVACY
        .iter()
        .position(|item| *item == value)
        .unwrap_or(usize::MAX)
}
fn max_privacy<'a>(left: &'a str, right: &'a str) -> &'a str {
    if privacy_rank(left) >= privacy_rank(right) {
        left
    } else {
        right
    }
}
fn bytes_len<R: VerifiedRecord>(
    data: &Map<String, JsonValue>,
    field: &str,
    length: usize,
    record: &R,
) -> Result<(), SemanticError> {
    let bytes = data
        .get(field)
        .and_then(JsonValue::as_object)
        .and_then(|object| object.get("$bytes_hex"))
        .and_then(JsonValue::as_str)
        .and_then(hex_bytes);
    if bytes.is_some_and(|bytes| bytes.len() == length) {
        Ok(())
    } else {
        fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            format!("{field} has wrong byte length"),
        )
    }
}
fn fixed_confidence<R: VerifiedRecord>(
    value: Option<&JsonValue>,
    record: &R,
) -> Result<(), SemanticError> {
    let Some(object) = value.and_then(JsonValue::as_object) else {
        return fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            "confidence must be fixed-point",
        );
    };
    let keys: BTreeSet<_> = object.keys().map(String::as_str).collect();
    if keys != BTreeSet::from(["coefficient", "scale"]) {
        return fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            "invalid fixed-point fields",
        );
    }
    let coefficient = object["coefficient"]
        .as_i64()
        .ok_or_else(|| field_error(record, "invalid coefficient"))?;
    let scale = object["scale"]
        .as_u64()
        .ok_or_else(|| field_error(record, "invalid scale"))?;
    if scale > 18
        || coefficient < 0
        || coefficient as u128 > 10_u128.pow(scale as u32)
        || (coefficient == 0 && scale != 0)
        || (scale > 0 && coefficient % 10 == 0)
    {
        fail(
            SemanticErrorCode::PayloadFieldInvalid,
            record,
            "non-normalized confidence",
        )
    } else {
        Ok(())
    }
}
fn insert<R: VerifiedRecord>(
    map: &mut BTreeMap<String, JsonValue>,
    id: String,
    value: JsonValue,
    record: &R,
) -> Result<(), SemanticError> {
    if map.insert(id, value).is_some() {
        fail(
            SemanticErrorCode::IdentifierConflict,
            record,
            "identifier conflict",
        )
    } else {
        Ok(())
    }
}
fn has_reference(state: &State, id: &str) -> bool {
    state.accepted_event_ids.iter().any(|value| value == id)
        || state.evidence.contains_key(id)
        || state.policies.contains_key(id)
        || state.models.contains_key(id)
}
fn subset(items: &[String], container: &JsonValue) -> bool {
    container.as_array().is_some_and(|values| {
        items
            .iter()
            .all(|item| values.contains(&JsonValue::String(item.clone())))
    })
}
fn subset_json(items: &JsonValue, container: &JsonValue) -> bool {
    items.as_array().is_some_and(|items| {
        container
            .as_array()
            .is_some_and(|container| items.iter().all(|item| container.contains(item)))
    })
}
fn principal_has_capability(
    state: &State,
    principal: &str,
    key: &str,
    capability: &str,
    sequence: u64,
) -> bool {
    state.grants.values().any(|grant| {
        grant["principal_id"] == principal
            && grant["key_id"] == key
            && grant["valid_from_log_sequence"]
                .as_u64()
                .is_some_and(|start| start <= sequence)
            && (grant["valid_to_log_sequence"].is_null()
                || grant["valid_to_log_sequence"]
                    .as_u64()
                    .is_some_and(|end| sequence < end))
            && grant["capabilities"]
                .as_array()
                .is_some_and(|items| items.iter().any(|item| item == capability || item == "*"))
    })
}
fn topology_cycle(edges: &BTreeMap<String, JsonValue>) -> bool {
    fn visit<'a>(
        node: &'a str,
        graph: &BTreeMap<&'a str, Vec<&'a str>>,
        visiting: &mut BTreeSet<&'a str>,
        done: &mut BTreeSet<&'a str>,
    ) -> bool {
        if done.contains(node) {
            return false;
        }
        if !visiting.insert(node) {
            return true;
        }
        if graph.get(node).is_some_and(|children| {
            children
                .iter()
                .any(|child| visit(child, graph, visiting, done))
        }) {
            return true;
        }
        visiting.remove(node);
        done.insert(node);
        false
    }
    let mut graph: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
    for edge in edges
        .values()
        .filter(|edge| edge["edgeType"] == "DEPENDS_ON")
    {
        if let (Some(source), Some(target)) = (
            edge["sourceModelId"].as_str(),
            edge["targetModelId"].as_str(),
        ) {
            graph.entry(source).or_default().push(target);
        }
    }
    let mut visiting = BTreeSet::new();
    let mut done = BTreeSet::new();
    graph
        .keys()
        .any(|node| visit(node, &graph, &mut visiting, &mut done))
}
fn integer(value: &Value) -> Option<i64> {
    match value {
        Value::Unsigned(value) => i64::try_from(*value).ok(),
        Value::Negative(value) => Some(*value),
        _ => None,
    }
}
fn hex_string(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        output.push(HEX[(byte >> 4) as usize] as char);
        output.push(HEX[(byte & 15) as usize] as char);
    }
    output
}
fn hex_bytes(value: &str) -> Option<Vec<u8>> {
    if !value.len().is_multiple_of(2) {
        return None;
    }
    (0..value.len())
        .step_by(2)
        .map(|index| u8::from_str_radix(&value[index..index + 2], 16).ok())
        .collect()
}
fn semantic<R: VerifiedRecord>(
    record: &R,
    code: SemanticErrorCode,
    message: impl Into<String>,
) -> SemanticError {
    SemanticError::at(code, record.log_sequence(), record.event_kind(), message)
}
fn field_error<R: VerifiedRecord>(record: &R, message: impl Into<String>) -> SemanticError {
    semantic(record, SemanticErrorCode::PayloadFieldInvalid, message)
}
fn fail<T, R: VerifiedRecord>(
    code: SemanticErrorCode,
    record: &R,
    message: impl Into<String>,
) -> Result<T, SemanticError> {
    Err(semantic(record, code, message))
}
fn command_error(code: SemanticErrorCode, message: impl Into<String>) -> SemanticError {
    SemanticError::at(code, 0, "command", message)
}
fn command_fail<T>(
    code: SemanticErrorCode,
    message: impl Into<String>,
) -> Result<T, SemanticError> {
    Err(command_error(code, message))
}
fn command_shape() -> SemanticError {
    command_error(
        SemanticErrorCode::CommandUnsupported,
        "missing command argument",
    )
}
fn stable_code(code: SemanticErrorCode) -> SemanticErrorCode {
    match code {
        SemanticErrorCode::InvalidField
        | SemanticErrorCode::EnvelopeShape
        | SemanticErrorCode::PayloadCbor => SemanticErrorCode::PayloadFieldInvalid,
        SemanticErrorCode::DuplicateId => SemanticErrorCode::IdentifierConflict,
        SemanticErrorCode::MissingReference | SemanticErrorCode::HplRequestMissing => {
            SemanticErrorCode::ReferenceNotFound
        }
        SemanticErrorCode::InvalidLifecycle => SemanticErrorCode::LifecyclePreconditionMissing,
        SemanticErrorCode::FamilyKindNotAllowed | SemanticErrorCode::InvalidModelKind => {
            SemanticErrorCode::FamilyKindNotAllowed
        }
        SemanticErrorCode::PossibleWorldScopeViolation => SemanticErrorCode::WorldScopeViolation,
        SemanticErrorCode::DependencyCycle => SemanticErrorCode::TopologyCycle,
        SemanticErrorCode::AuthorityBindingMismatch
        | SemanticErrorCode::QueryUnauthorized
        | SemanticErrorCode::AuthorizationScopeMismatch => {
            SemanticErrorCode::AuthorityScopeViolation
        }
        SemanticErrorCode::AuthorizationMissing
        | SemanticErrorCode::AuthorizationOperationDenied => SemanticErrorCode::GrantNotFound,
        other => other,
    }
}
