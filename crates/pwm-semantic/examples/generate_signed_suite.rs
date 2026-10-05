use std::collections::BTreeMap;
use std::{env, fs, path::Path};

use pwm_canonical::{AppendReceiptBodyCid, EventBodyCid, PayloadCid, Value, encode};
use pwm_crypto::SigningKey;
use pwm_event::{
    AppendReceiptBody, EventBody, KeyRegistry, MemoryDag, SchemaRegistry, SignedAppendReceipt,
    SignedEvent,
};
use pwm_semantic::{
    ConformanceCommand, KeyVector, RecordVector, SchemaVector, SignedQuery, SignedSemanticSource,
    TrustAnchor, VectorBundle, evaluate_signed_source_json,
};
use serde_json::{Value as JsonValue, json};

const SCOPE: &str = "person:alice";
const ROOT_KEY_ID: &str = "key:test-root";
const APPENDER_KEY_ID: &str = "key:test-appender";
const PROPOSER_KEY_ID: &str = "key:test-proposer";
const PLANNER_KEY_ID: &str = "key:test-planner";
const KINDS: [&str; 23] = [
    "pwm.genesis",
    "pwm.evidence",
    "pwm.policy",
    "pwm.model.propose",
    "pwm.model.review",
    "pwm.model.accept",
    "pwm.model.update",
    "pwm.model.dispute",
    "pwm.model.revoke",
    "pwm.privacy-boundary.approve",
    "pwm.privacy-boundary.revoke",
    "pwm.contradiction.propose",
    "pwm.contradiction.review",
    "pwm.contradiction.accept",
    "pwm.contradiction.resolve",
    "pwm.topology.edge",
    "pwm.possible-world",
    "pwm.query-authority",
    "hpl.request",
    "hpl.authorization",
    "hpl.projection",
    "hpl.revoke",
    "pwm.conformance.evaluate",
];

#[derive(Clone)]
struct Spec {
    kind: &'static str,
    data: JsonValue,
    signer: &'static str,
}

struct Builder {
    root: SigningKey,
    appender: SigningKey,
    proposer: SigningKey,
    planner: SigningKey,
    keys: KeyRegistry,
    schemas: SchemaRegistry,
    dag: MemoryDag,
    records: Vec<RecordVector>,
    parent: Option<EventBodyCid>,
    author_sequences: BTreeMap<&'static str, u64>,
}

impl Builder {
    fn new() -> Self {
        let root = SigningKey::from_seed([71; 32]);
        let appender = SigningKey::from_seed([72; 32]);
        let proposer = SigningKey::from_seed([73; 32]);
        let planner = SigningKey::from_seed([74; 32]);
        let mut keys = KeyRegistry::new();
        keys.activate(ROOT_KEY_ID, root.public_key(), 0).unwrap();
        keys.activate(PROPOSER_KEY_ID, proposer.public_key(), 0)
            .unwrap();
        keys.activate(PLANNER_KEY_ID, planner.public_key(), 0)
            .unwrap();
        let schemas = SchemaRegistry::new(KINDS.map(|kind| (kind, "1.0.0"))).unwrap();
        let dag = MemoryDag::new(APPENDER_KEY_ID, appender.public_key());
        Self {
            root,
            appender,
            proposer,
            planner,
            keys,
            schemas,
            dag,
            records: Vec::new(),
            parent: None,
            author_sequences: BTreeMap::new(),
        }
    }

    fn append(&mut self, spec: &Spec) {
        let sequence = self.records.len() as u64;
        let (key_id, signer) = match spec.signer {
            "proposer" => (PROPOSER_KEY_ID, &self.proposer),
            "planner" => (PLANNER_KEY_ID, &self.planner),
            _ => (ROOT_KEY_ID, &self.root),
        };
        let author_sequence = *self.author_sequences.get(spec.signer).unwrap_or(&0);
        let payload = encode(&Value::Map(vec![
            (
                "profile".into(),
                Value::Text("pwm-signed-semantics-v1".into()),
            ),
            ("schema_version".into(), Value::Text("1.0.0".into())),
            ("data".into(), cbor(&spec.data)),
            ("valid_from_ns".into(), Value::Unsigned(0)),
            ("valid_to_ns".into(), Value::Null),
        ]))
        .unwrap();
        let parents = self.parent.into_iter().collect();
        let body = EventBody::new(
            "1.0.0",
            spec.kind,
            key_id,
            SCOPE,
            parents,
            author_sequence,
            1_800_000_000_000_000_000_i64 + sequence as i64,
            PayloadCid::from_canonical_bytes(&payload),
        )
        .unwrap();
        let event = SignedEvent::sign(body, signer).unwrap();
        let receipt = self
            .dag
            .append(
                &event,
                &payload,
                1_800_000_000_100_000_000_i64 + sequence as i64,
                &self.keys,
                &self.schemas,
                &self.appender,
            )
            .unwrap();
        self.parent = Some(event.body_cid);
        self.author_sequences
            .insert(spec.signer, author_sequence + 1);
        self.records.push(RecordVector {
            body_cbor_hex: hex::encode(event.body.canonical_bytes().unwrap()),
            body_cid: event.body_cid.to_string(),
            event_signature_hex: hex::encode(event.signature.as_bytes()),
            payload_cbor_hex: hex::encode(payload),
            receipt_body_cbor_hex: hex::encode(receipt.receipt_body.canonical_bytes().unwrap()),
            receipt_cid: receipt.receipt_cid.to_string(),
            receipt_signature_hex: hex::encode(receipt.signature.as_bytes()),
        });
    }

    fn source(mut self, id: &str, specs: &[Spec]) -> SignedSemanticSource {
        for spec in specs {
            self.append(spec);
        }
        let root_hex = hex::encode(self.root.public_key().as_bytes());
        SignedSemanticSource {
            source_version: "1.0.0".into(),
            source_id: id.into(),
            profile: "pwm-signed-semantics-v1".into(),
            trust_anchor: TrustAnchor {
                key_id: ROOT_KEY_ID.into(),
                public_key_hex: root_hex.clone(),
            },
            bundle: VectorBundle {
                profile: "pwm-public-provenance-v1".into(),
                appender_key_id: APPENDER_KEY_ID.into(),
                appender_public_key_hex: hex::encode(self.appender.public_key().as_bytes()),
                author_keys: vec![
                    KeyVector {
                        key_id: ROOT_KEY_ID.into(),
                        public_key_hex: root_hex,
                        active_from_log_sequence: 0,
                        revoked_at_log_sequence: None,
                    },
                    KeyVector {
                        key_id: PROPOSER_KEY_ID.into(),
                        public_key_hex: hex::encode(self.proposer.public_key().as_bytes()),
                        active_from_log_sequence: 0,
                        revoked_at_log_sequence: None,
                    },
                    KeyVector {
                        key_id: PLANNER_KEY_ID.into(),
                        public_key_hex: hex::encode(self.planner.public_key().as_bytes()),
                        active_from_log_sequence: 0,
                        revoked_at_log_sequence: None,
                    },
                ],
                schemas: KINDS
                    .iter()
                    .map(|kind| SchemaVector {
                        event_kind: (*kind).into(),
                        schema_version: "1.0.0".into(),
                    })
                    .collect(),
                records: self.records,
            },
            command: ConformanceCommand {
                operation: "REDUCE".into(),
                evaluation_log_sequence: specs.len() as u64 - 1,
                query: None,
                projection_id: None,
                evaluation_id: None,
            },
        }
    }
}

fn cbor(value: &JsonValue) -> Value {
    match value {
        JsonValue::Null => Value::Null,
        JsonValue::Bool(value) => Value::Bool(*value),
        JsonValue::Number(value) if value.is_u64() => Value::Unsigned(value.as_u64().unwrap()),
        JsonValue::Number(value) => Value::Negative(value.as_i64().unwrap()),
        JsonValue::String(value) => Value::Text(value.clone()),
        JsonValue::Array(values) => Value::Array(values.iter().map(cbor).collect()),
        JsonValue::Object(values) if values.len() == 1 && values.contains_key("$bytes_hex") => {
            Value::Bytes(hex::decode(values["$bytes_hex"].as_str().unwrap()).unwrap())
        }
        JsonValue::Object(values) => Value::Map(
            values
                .iter()
                .map(|(key, value)| (key.clone(), cbor(value)))
                .collect(),
        ),
    }
}

fn spec(kind: &'static str, data: JsonValue) -> Spec {
    Spec {
        kind,
        data,
        signer: "root",
    }
}

fn proposer_spec(kind: &'static str, data: JsonValue) -> Spec {
    Spec {
        kind,
        data,
        signer: "proposer",
    }
}

fn planner_spec(kind: &'static str, data: JsonValue) -> Spec {
    Spec {
        kind,
        data,
        signer: "planner",
    }
}

fn genesis(operations: JsonValue, capabilities: JsonValue) -> Spec {
    let capabilities = if capabilities == json!(["*"]) {
        json!(["*", "pwm.review.self"])
    } else {
        capabilities
    };
    spec(
        "pwm.genesis",
        json!({
            "scope_id":SCOPE, "root_principal_id":SCOPE, "root_key_id":ROOT_KEY_ID,
            "principals":[{"principal_id":SCOPE,"principal_class":"PERSON"},{"principal_id":"agent:planner","principal_class":"AGENT"}],
            "grants":[{"grant_id":"grant:root","principal_id":SCOPE,"key_id":ROOT_KEY_ID,
                "scope_id":SCOPE,"operations":operations,"capabilities":capabilities,"grant_class":"ROOT",
                "valid_from_log_sequence":0,"valid_to_log_sequence":null},
                {"grant_id":"grant:planner","principal_id":"agent:planner","key_id":PLANNER_KEY_ID,
                "scope_id":SCOPE,"operations":["EVIDENCE_CREATE"],"capabilities":["pwm.evidence.write"],"grant_class":"AUTHOR",
                "valid_from_log_sequence":0,"valid_to_log_sequence":null},
                {"grant_id":"grant:proposer","principal_id":SCOPE,"key_id":PROPOSER_KEY_ID,
                "scope_id":SCOPE,"operations":["MODEL_PROPOSE"],"capabilities":["pwm.model.propose"],"grant_class":"AUTHOR",
                "valid_from_log_sequence":0,"valid_to_log_sequence":null}]
        }),
    )
}

fn evidence(id: &str, privacy: &str) -> Spec {
    planner_spec(
        "pwm.evidence",
        json!({"evidence_id":id,"evidence_kind":"DOCUMENT","subject_ids":[SCOPE],
        "source_uri":null,"content_digest":{"$bytes_hex":"11".repeat(32)},"privacy_class":privacy,"properties":{}}),
    )
}

fn policy(id: &str) -> Spec {
    spec(
        "pwm.policy",
        json!({
            "policy_id":id,"policy_profile":"pwm-declassification-v1",
            "content_digest":{"$bytes_hex":"44".repeat(32)},"privacy_floor":"PUBLIC","properties":{}
        }),
    )
}

#[allow(clippy::too_many_arguments)]
fn proposal(
    id: &str,
    proposal: &str,
    family: &str,
    kind: &str,
    subjects: JsonValue,
    perspective: JsonValue,
    world: &str,
    evidence: JsonValue,
    properties: JsonValue,
) -> Spec {
    proposer_spec(
        "pwm.model.propose",
        json!({"proposal_id":proposal,"model_id":id,"family":family,"kind":kind,
        "subject_ids":subjects,"perspective_id":perspective,"world_id":world,"evidence_ids":evidence,
        "declared_privacy_class":"PERSONAL","properties":properties,"confidence":{"coefficient":9,"scale":1}}),
    )
}

#[allow(clippy::too_many_arguments)]
fn lifecycle(
    id: &str,
    tag: &str,
    family: &str,
    kind: &str,
    subjects: JsonValue,
    perspective: JsonValue,
    world: &str,
    evidence: JsonValue,
    properties: JsonValue,
) -> Vec<Spec> {
    let proposal_id = format!("proposal:{tag}");
    let review_id = format!("review:{tag}");
    vec![
        proposal(
            id,
            &proposal_id,
            family,
            kind,
            subjects,
            perspective,
            world,
            evidence,
            properties,
        ),
        spec(
            "pwm.model.review",
            json!({"review_id":review_id,"proposal_id":proposal_id,"reviewer_principal_id":SCOPE,"decision":"APPROVE","reason":"fixture"}),
        ),
        spec(
            "pwm.model.accept",
            json!({"model_id":id,"proposal_id":proposal_id,"review_id":review_id}),
        ),
    ]
}

fn comprehensive() -> Vec<Spec> {
    let mut events = vec![
        genesis(json!(["*"]), json!(["*"])),
        evidence("e:policy", "PUBLIC"),
        evidence("e:sensitive", "SENSITIVE"),
        policy("policy:one"),
        spec(
            "pwm.possible-world",
            json!({"world_id":"world:possible","parent_world_id":"world:actual","base_state_cid":{"$bytes_hex":"22".repeat(32)},"base_time_ns":0,"declared_privacy_class":"PERSONAL","purpose":"fixture"}),
        ),
    ];
    events.extend(lifecycle(
        "model:self",
        "self",
        "pwm.preference",
        "SELF",
        json!([SCOPE]),
        json!(SCOPE),
        "world:actual",
        json!(["e:sensitive"]),
        json!({"preference":"tea"}),
    ));
    events.extend(lifecycle(
        "model:relationship",
        "relationship",
        "pwm.relationship",
        "RELATIONSHIP",
        json!(["person:bob", "person:alice"]),
        json!(SCOPE),
        "world:actual",
        json!(["e:sensitive"]),
        json!({"strength":"close"}),
    ));
    events.extend(lifecycle(
        "model:world",
        "world",
        "pwm.physical-environment",
        "WORLD",
        json!(["place:home"]),
        json!(SCOPE),
        "world:actual",
        json!(["e:policy"]),
        json!({"room":"study"}),
    ));
    events.extend(lifecycle(
        "model:meta",
        "meta",
        "pwm.models-of-models",
        "META",
        json!(["model:self"]),
        json!(SCOPE),
        "world:actual",
        json!(["e:policy"]),
        json!({"targetModelId":"model:self"}),
    ));
    events.extend(lifecycle(
        "model:possible",
        "possible",
        "pwm.imagination-possible-worlds",
        "POSSIBLE_WORLD",
        json!([SCOPE]),
        json!(SCOPE),
        "world:possible",
        json!(["e:policy"]),
        json!({"parentWorldId":"world:actual"}),
    ));
    events.push(proposal(
        "model:self:v2",
        "proposal:self-v2",
        "pwm.preference",
        "SELF",
        json!([SCOPE]),
        json!(SCOPE),
        "world:actual",
        json!(["e:sensitive"]),
        json!({"preference":"coffee"}),
    ));
    events.push(spec("pwm.model.review", json!({"review_id":"review:self-v2","proposal_id":"proposal:self-v2","reviewer_principal_id":SCOPE,"decision":"APPROVE","reason":"fixture"})));
    events.push(spec("pwm.model.update", json!({"model_id":"model:self:v2","previous_model_id":"model:self","proposal_id":"proposal:self-v2","review_id":"review:self-v2"})));
    events.push(spec(
        "pwm.model.dispute",
        json!({"model_id":"model:relationship","reason":"fixture","evidence_ids":["e:policy"]}),
    ));
    events.push(spec(
        "pwm.model.revoke",
        json!({"model_id":"model:relationship","reason":"fixture"}),
    ));
    events.push(spec("pwm.privacy-boundary.approve", json!({"boundary_id":"boundary:one","boundary_kind":"REDACTION","policy_id":"policy:one","source_ids":["model:self:v2"],"input_privacy_class":"SENSITIVE","output_privacy_class":"PERSONAL","released_fields":["preference"],"approver_principal_id":SCOPE,"expires_at_log_sequence":100})));
    events.push(spec("pwm.privacy-boundary.approve", json!({"boundary_id":"boundary:proof","boundary_kind":"PROOF","policy_id":"policy:one","source_ids":["model:meta"],"input_privacy_class":"PERSONAL","output_privacy_class":"LOW","released_fields":["targetModelId"],"approver_principal_id":SCOPE,"expires_at_log_sequence":100})));
    events.push(spec("pwm.contradiction.propose", json!({"proposal_id":"proposal:contradiction","contradiction_id":"contradiction:one","contradiction_type":"INCONSISTENT","reference_ids":["model:world","model:self:v2"],"world_id":"world:actual","evidence_ids":["e:policy"],"explanation":"fixture"})));
    events.push(spec("pwm.contradiction.review", json!({"review_id":"review:contradiction","proposal_id":"proposal:contradiction","reviewer_principal_id":SCOPE,"decision":"APPROVE","reason":"fixture"})));
    events.push(spec("pwm.contradiction.accept", json!({"contradiction_id":"contradiction:one","proposal_id":"proposal:contradiction","review_id":"review:contradiction"})));
    events.push(spec("pwm.contradiction.resolve", json!({"resolution_id":"resolution:one","contradiction_id":"contradiction:one","status":"EXPLAINED","resolver_principal_id":SCOPE,"explanation":"fixture","evidence_ids":["e:policy"]})));
    events.push(spec("pwm.topology.edge", json!({"edge_id":"edge:one","source_model_id":"model:self:v2","target_model_id":"model:meta","edge_type":"DEPENDS_ON","world_id":"world:actual","evidence_ids":["e:policy"],"declared_privacy_class":"PERSONAL"})));
    events.push(spec("pwm.query-authority", json!({"authority_id":"authority:one","principal_id":SCOPE,"recipient_id":"recipient:test","purpose":"assist","world_ids":["world:actual"],"subject_ids":["model:self","place:home","person:alice"],"perspective_ids":[SCOPE],"families":["pwm.preference","pwm.models-of-models","pwm.physical-environment"],"privacy_ceiling":"SENSITIVE","allow_disputed":true,"valid_from_log_sequence":0,"valid_to_log_sequence":100})));
    events.push(spec("hpl.request", json!({"request_id":"request:one","requester_principal_id":SCOPE,"recipient_id":"recipient:test","purpose":"assist","world_id":"world:actual","model_ids":["model:self:v2"],"requested_fields":["preference"],"maximum_privacy_class":"SENSITIVE","retention_until_ns":99,"capabilities":[]})));
    events.push(spec("hpl.authorization", json!({"authorization_id":"authorization:one","request_id":"request:one","query_authority_id":"authority:one","authorizer_principal_id":SCOPE,"allowed_model_ids":["model:self:v2"],"allowed_fields":["preference"],"privacy_ceiling":"SENSITIVE","valid_to_log_sequence":100})));
    events.push(spec("hpl.projection", json!({"projection_id":"projection:one","authorization_id":"authorization:one","recipient_id":"recipient:test","purpose":"assist","world_id":"world:actual","model_ids":["model:self:v2"],"released_fields":["preference"],"effective_privacy_class":"PERSONAL","boundary_ids":["boundary:one"],"content_digest":{"$bytes_hex":"33".repeat(32)},"expires_at_ns":99})));
    events.push(spec(
        "pwm.privacy-boundary.revoke",
        json!({"boundary_id":"boundary:proof","reason":"fixture complete"}),
    ));
    events.push(spec(
        "hpl.revoke",
        json!({"target_type":"PROJECTION","target_id":"projection:one","reason":"fixture"}),
    ));
    events
}

fn semantic_cases() -> Vec<(&'static str, Vec<Spec>, &'static str)> {
    let base = || {
        vec![
            genesis(json!(["*"]), json!(["*"])),
            evidence("e:one", "PERSONAL"),
        ]
    };
    vec![
        (
            "unauthorized-operation",
            vec![
                genesis(json!(["EVIDENCE_CREATE"]), json!(["*"])),
                spec(
                    "pwm.possible-world",
                    json!({"world_id":"world:x","parent_world_id":"world:actual","base_state_cid":{"$bytes_hex":"22".repeat(32)},"base_time_ns":0,"declared_privacy_class":"PERSONAL","purpose":"fixture"}),
                ),
            ],
            "GRANT_NOT_FOUND",
        ),
        (
            "invalid-principal-grant",
            vec![spec(
                "pwm.genesis",
                json!({"scope_id":SCOPE,"root_principal_id":SCOPE,"root_key_id":ROOT_KEY_ID,"principals":[{"principal_id":SCOPE,"principal_class":"PERSON"}],"grants":[{"grant_id":"grant:root","principal_id":"person:missing","key_id":ROOT_KEY_ID,"scope_id":SCOPE,"operations":["*"],"capabilities":["*"],"grant_class":"ROOT","valid_from_log_sequence":0,"valid_to_log_sequence":null}]}),
            )],
            "PAYLOAD_FIELD_INVALID",
        ),
        (
            "family-kind",
            {
                let mut v = base();
                v.push(proposal(
                    "model:bad",
                    "proposal:bad",
                    "pwm.preference",
                    "RELATIONSHIP",
                    json!(["person:bob", "person:alice"]),
                    json!(SCOPE),
                    "world:actual",
                    json!(["e:one"]),
                    json!({}),
                ));
                v
            },
            "FAMILY_KIND_NOT_ALLOWED",
        ),
        (
            "subject-perspective",
            {
                let mut v = base();
                v.push(proposal(
                    "model:bad",
                    "proposal:bad",
                    "pwm.preference",
                    "SELF",
                    json!(["person:bob"]),
                    json!(SCOPE),
                    "world:actual",
                    json!(["e:one"]),
                    json!({}),
                ));
                v
            },
            "FAMILY_KIND_NOT_ALLOWED",
        ),
        (
            "false-effective-privacy",
            {
                let mut v = base();
                let mut p = proposal(
                    "model:bad",
                    "proposal:bad",
                    "pwm.preference",
                    "SELF",
                    json!([SCOPE]),
                    json!(SCOPE),
                    "world:actual",
                    json!(["e:one"]),
                    json!({}),
                );
                p.data
                    .as_object_mut()
                    .unwrap()
                    .insert("effective_privacy_class".into(), json!("PUBLIC"));
                v.push(p);
                v
            },
            "PAYLOAD_FIELD_INVALID",
        ),
        (
            "unauthorized-declassification",
            {
                let mut v = base();
                v.push(spec("pwm.privacy-boundary.approve",json!({"boundary_id":"boundary:bad","boundary_kind":"REDACTION","policy_id":"e:one","source_ids":["e:one"],"input_privacy_class":"PERSONAL","output_privacy_class":"PUBLIC","released_fields":["x"],"approver_principal_id":"person:bob","expires_at_log_sequence":99})));
                v
            },
            "AUTHORITY_SCOPE_VIOLATION",
        ),
        (
            "contradiction-transition",
            {
                let mut v = base();
                v.push(spec("pwm.contradiction.accept",json!({"contradiction_id":"missing","proposal_id":"missing","review_id":"missing"})));
                v
            },
            "LIFECYCLE_PRECONDITION_MISSING",
        ),
        (
            "hpl-binding",
            {
                let mut v = base();
                v.extend(lifecycle(
                    "model:one",
                    "one",
                    "pwm.preference",
                    "SELF",
                    json!([SCOPE]),
                    json!(SCOPE),
                    "world:actual",
                    json!(["e:one"]),
                    json!({"field":"x"}),
                ));
                v.push(spec("hpl.request",json!({"request_id":"request:bad","requester_principal_id":"person:bob","recipient_id":"recipient:test","purpose":"assist","world_id":"world:actual","model_ids":["model:one"],"requested_fields":["x"],"maximum_privacy_class":"PERSONAL","retention_until_ns":99,"capabilities":[]})));
                v
            },
            "AUTHORITY_SCOPE_VIOLATION",
        ),
        (
            "hpl-authorization-expired",
            {
                let mut v = comprehensive();
                let projection_sequence = v
                    .iter()
                    .position(|item| item.kind == "hpl.projection")
                    .unwrap() as u64;
                let authorization = v
                    .iter_mut()
                    .find(|item| item.kind == "hpl.authorization")
                    .unwrap();
                authorization
                    .data
                    .as_object_mut()
                    .unwrap()
                    .insert("valid_to_log_sequence".into(), json!(projection_sequence));
                v
            },
            "AUTHORITY_EXPIRED",
        ),
        (
            "hpl-projection-replay",
            {
                let mut v = comprehensive();
                let projection = v
                    .iter()
                    .find(|item| item.kind == "hpl.projection")
                    .unwrap()
                    .clone();
                v.push(projection);
                v
            },
            "IDENTIFIER_CONFLICT",
        ),
    ]
}

fn mutate_case(
    name: &str,
    mut source: SignedSemanticSource,
) -> (SignedSemanticSource, &'static str) {
    let records = &mut source.bundle.records;
    let expected = match name {
        "signature-mutation" => {
            records[0].event_signature_hex.replace_range(0..2, "00");
            "SIGNATURE_INVALID"
        }
        "payload-mutation" => {
            let last = records[0].payload_cbor_hex.len() - 2;
            records[0].payload_cbor_hex.replace_range(last.., "01");
            "CID_MISMATCH"
        }
        "body-cid-mismatch" => {
            let last = records[0].body_cid.len() - 1;
            let replacement = if &records[0].body_cid[last..] == "a" {
                "b"
            } else {
                "a"
            };
            records[0].body_cid.replace_range(last.., replacement);
            "CID_MISMATCH"
        }
        _ => unreachable!(),
    };
    source.source_id = format!("signed-semantic:{name}");
    (source, expected)
}

fn mutate_causal_case(
    name: &str,
    mut source: SignedSemanticSource,
) -> (SignedSemanticSource, &'static str) {
    let planner = SigningKey::from_seed([74; 32]);
    let appender = SigningKey::from_seed([72; 32]);
    let record = &mut source.bundle.records[1];
    let body_bytes = hex::decode(&record.body_cbor_hex).unwrap();
    let mut body = EventBody::from_canonical_bytes(&body_bytes).unwrap();
    let expected = match name {
        "unknown-parent" => {
            body.parent_event_cids = vec![EventBodyCid::from_canonical_bytes(
                &encode(&Value::Text("absent-parent".into())).unwrap(),
            )];
            "PARENT_INVALID"
        }
        "invalid-author-sequence" => {
            body.author_sequence = 2;
            "AUTHOR_SEQUENCE_INVALID"
        }
        "invalid-principal-scope" => {
            body.principal_scope = "person:mallory".into();
            "PARENT_INVALID"
        }
        _ => unreachable!(),
    };
    let event = SignedEvent::sign(body, &planner).unwrap();
    let old_receipt = AppendReceiptBody::from_canonical_bytes(
        &hex::decode(&record.receipt_body_cbor_hex).unwrap(),
    )
    .unwrap();
    let receipt_body = AppendReceiptBody {
        body_cid: event.body_cid,
        ingestion_time: old_receipt.ingestion_time,
        key_status_frontier_cid: old_receipt.key_status_frontier_cid,
        log_sequence: old_receipt.log_sequence,
        appender_key_id: old_receipt.appender_key_id,
    };
    let receipt_cid =
        AppendReceiptBodyCid::from_canonical_bytes(&receipt_body.canonical_bytes().unwrap());
    let receipt = SignedAppendReceipt {
        receipt_body,
        receipt_cid,
        signature_algorithm: "Ed25519".into(),
        signature: appender.sign_append_receipt(&receipt_cid),
    };
    record.body_cbor_hex = hex::encode(event.body.canonical_bytes().unwrap());
    record.body_cid = event.body_cid.to_string();
    record.event_signature_hex = hex::encode(event.signature.as_bytes());
    record.receipt_body_cbor_hex = hex::encode(receipt.receipt_body.canonical_bytes().unwrap());
    record.receipt_cid = receipt.receipt_cid.to_string();
    record.receipt_signature_hex = hex::encode(receipt.signature.as_bytes());
    source.source_id = format!("signed-semantic:{name}");
    (source, expected)
}

fn write_json(path: &Path, value: &impl serde::Serialize) {
    let mut bytes = serde_json::to_vec_pretty(value).unwrap();
    bytes.push(b'\n');
    fs::write(path, bytes).unwrap();
}

fn neutral_output(source: &SignedSemanticSource) -> JsonValue {
    let serialized = serde_json::to_string(source).unwrap();
    let mut value = serde_json::to_value(evaluate_signed_source_json(&serialized)).unwrap();
    value.as_object_mut().unwrap().remove("implementation");
    value
}

fn main() {
    let output = env::args()
        .nth(1)
        .expect("usage: generate_signed_suite OUTPUT_DIR");
    let root = Path::new(&output);
    let sources = root.join("sources");
    let vectors = root.join("vectors");
    fs::create_dir_all(&sources).unwrap();
    fs::create_dir_all(&vectors).unwrap();
    let comprehensive_specs = comprehensive();
    let projection_frontier = comprehensive_specs
        .iter()
        .position(|item| item.kind == "hpl.projection")
        .unwrap() as u64;
    let valid = Builder::new().source("signed-semantic:comprehensive", &comprehensive_specs);
    let mut cases = Vec::new();
    write_json(&sources.join("signed-semantic-comprehensive.json"), &valid);
    cases.push(json!({"case_id":"comprehensive","description":"Complete valid signed semantic history","polarity":"valid","source":valid.clone(),"expected":{"decision":"ACCEPT","output":neutral_output(&valid)}}));

    let mut query_source = valid.clone();
    query_source.source_id = "signed-semantic:comprehensive-query".into();
    query_source.command = ConformanceCommand {
        operation: "QUERY".into(),
        evaluation_log_sequence: projection_frontier,
        query: Some(SignedQuery {
            authority_id: "authority:one".into(),
            world_id: "world:actual".into(),
            as_of_valid_ns: 50,
            recipient_id: "recipient:test".into(),
            purpose: "assist".into(),
            model_ids: vec![
                "model:meta".into(),
                "model:self:v2".into(),
                "model:world".into(),
            ],
            include_disputed: false,
        }),
        projection_id: None,
        evaluation_id: None,
    };
    write_json(
        &sources.join("signed-semantic-comprehensive-query.json"),
        &query_source,
    );
    cases.push(json!({"case_id":"comprehensive-query","description":"Authenticated deterministic semantic query","polarity":"valid","source":query_source.clone(),"expected":{"decision":"ACCEPT","output":neutral_output(&query_source)}}));

    let mut project_source = valid.clone();
    project_source.source_id = "signed-semantic:comprehensive-hpl".into();
    project_source.command = ConformanceCommand {
        operation: "PROJECT".into(),
        evaluation_log_sequence: projection_frontier,
        query: None,
        projection_id: Some("projection:one".into()),
        evaluation_id: None,
    };
    write_json(
        &sources.join("signed-semantic-comprehensive-hpl.json"),
        &project_source,
    );
    cases.push(json!({"case_id":"comprehensive-hpl","description":"Authenticated bounded HPL projection before revocation","polarity":"valid","source":project_source.clone(),"expected":{"decision":"ACCEPT","output":neutral_output(&project_source)}}));
    for (name, specs, error) in semantic_cases() {
        let source = Builder::new().source(&format!("signed-semantic:{name}"), &specs);
        write_json(
            &sources.join(format!("signed-semantic-{name}.json")),
            &source,
        );
        let rejected = serde_json::to_value(evaluate_signed_source_json(
            &serde_json::to_string(&source).unwrap(),
        ))
        .unwrap();
        cases.push(json!({"case_id":name,"description":format!("Semantic rejection: {name}"),"polarity":"invalid","source":source.clone(),"expected":{"decision":"REJECT","error_code":error,"state_digest_unchanged":true,"accepted_prefix_state_sha256":rejected["state_sha256"]}}));
        if name == "family-kind" {
            let mut combined = source.clone();
            combined.source_id = "signed-semantic:signature-and-semantic-invalid".into();
            let last = combined.bundle.records.last_mut().unwrap();
            last.event_signature_hex.replace_range(0..2, "00");
            write_json(
                &sources.join("signed-semantic-signature-and-semantic-invalid.json"),
                &combined,
            );
            let rejected = serde_json::to_value(evaluate_signed_source_json(
                &serde_json::to_string(&combined).unwrap(),
            ))
            .unwrap();
            cases.push(json!({"case_id":"signature-and-semantic-invalid","description":"Cryptographic signature failure precedes semantic family-kind failure","polarity":"invalid","source":combined,"expected":{"decision":"REJECT","error_code":"SIGNATURE_INVALID","state_digest_unchanged":true,"accepted_prefix_state_sha256":rejected["state_sha256"]}}));
        }
    }
    let simple = Builder::new().source(
        "signed-semantic:transport-base",
        &[
            genesis(json!(["*"]), json!(["*"])),
            evidence("e:one", "LOW"),
        ],
    );
    for name in [
        "signature-mutation",
        "payload-mutation",
        "body-cid-mismatch",
    ] {
        let (source, error) = mutate_case(name, simple.clone());
        write_json(
            &sources.join(format!("signed-semantic-{name}.json")),
            &source,
        );
        let rejected = serde_json::to_value(evaluate_signed_source_json(
            &serde_json::to_string(&source).unwrap(),
        ))
        .unwrap();
        cases.push(json!({"case_id":name,"description":format!("Transport rejection: {name}"),"polarity":"invalid","source":source,"expected":{"decision":"REJECT","error_code":error,"state_digest_unchanged":true,"accepted_prefix_state_sha256":rejected["state_sha256"]}}));
    }
    for name in [
        "unknown-parent",
        "invalid-author-sequence",
        "invalid-principal-scope",
    ] {
        let (source, error) = mutate_causal_case(name, simple.clone());
        write_json(
            &sources.join(format!("signed-semantic-{name}.json")),
            &source,
        );
        let rejected = serde_json::to_value(evaluate_signed_source_json(
            &serde_json::to_string(&source).unwrap(),
        ))
        .unwrap();
        cases.push(json!({"case_id":name,"description":format!("Causal rejection: {name}"),"polarity":"invalid","source":source,"expected":{"decision":"REJECT","error_code":error,"state_digest_unchanged":true,"accepted_prefix_state_sha256":rejected["state_sha256"]}}));
    }
    let suite = json!({"suite_version":"1.0.0","suite_id":"PWM-SIGNED-SEMANTICS-V1","profile":"pwm-signed-semantics-v1","profile_status":"PROVISIONAL","description":"Deterministic signed semantic interoperability suite","trust_anchor":valid.trust_anchor,"cases":cases});
    write_json(&vectors.join("signed-semantic-suite.json"), &suite);
}
