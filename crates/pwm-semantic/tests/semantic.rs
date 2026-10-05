use std::collections::BTreeSet;

use pwm_canonical::{Value, encode};
use pwm_semantic::{
    ACTUAL_WORLD, ModelStatus, OwnedVerifiedRecord, PrivacyClass, SemanticEngine,
    SemanticErrorCode, SemanticQuery, evaluate_json,
};
use serde_json::{Value as JsonValue, json};

fn cbor_value(value: &JsonValue) -> Value {
    match value {
        JsonValue::Null => Value::Null,
        JsonValue::Bool(value) => Value::Bool(*value),
        JsonValue::Number(value) if value.as_u64().is_some() => {
            Value::Unsigned(value.as_u64().unwrap())
        }
        JsonValue::Number(value) => Value::Negative(value.as_i64().unwrap()),
        JsonValue::String(value) => Value::Text(value.clone()),
        JsonValue::Array(values) => Value::Array(values.iter().map(cbor_value).collect()),
        JsonValue::Object(values) => Value::Map(
            values
                .iter()
                .map(|(key, value)| (key.clone(), cbor_value(value)))
                .collect(),
        ),
    }
}

fn record(sequence: u64, kind: &str, data: JsonValue) -> OwnedVerifiedRecord {
    let envelope = Value::Map(vec![
        (
            "profile".into(),
            Value::Text("pwm-signed-semantics-v1".into()),
        ),
        ("schema_version".into(), Value::Text("1.0.0".into())),
        ("data".into(), cbor_value(&data)),
        ("valid_from_ns".into(), Value::Null),
        ("valid_to_ns".into(), Value::Null),
    ]);
    OwnedVerifiedRecord {
        schema_version: "1.0.0".into(),
        event_kind: kind.into(),
        author_key_id: "key:self".into(),
        principal_scope: "person:self".into(),
        log_sequence: sequence,
        payload_cbor: encode(&envelope).unwrap(),
        event_body_cid: None,
        parent_event_cids: Vec::new(),
    }
}

fn genesis(operations: &[&str]) -> OwnedVerifiedRecord {
    record(
        0,
        "pwm.genesis",
        json!({"grants": [{
            "keyId": "key:self", "principalScope": "person:self", "operations": operations,
            "activeFromLogSequence": 0, "revokedAtLogSequence": null
        }]}),
    )
}

fn model_data(id: &str, state: JsonValue) -> JsonValue {
    json!({
        "modelId": id, "familyId": "pwm.preference", "kind": "SELF",
        "subjectIds": ["person:self"], "perspective": "person:self", "state": state,
        "confidencePpm": 800000, "privacyClass": "PERSONAL", "evidenceRefs": ["e:1"]
    })
}

fn accepted_model_records(start: u64, id: &str, state: JsonValue) -> Vec<OwnedVerifiedRecord> {
    vec![
        record(start, "pwm.model.proposed", model_data(id, state)),
        record(
            start + 1,
            "pwm.model.reviewed",
            json!({"modelId": id, "decision": "ACCEPT", "reviewer": "person:self"}),
        ),
        record(start + 2, "pwm.model.accepted", json!({"modelId": id})),
    ]
}

#[test]
fn authorization_precedence_is_key_then_scope_then_operation() {
    let mut engine = SemanticEngine::new();
    engine.apply(&genesis(&["pwm.model.*"])).unwrap();

    let mut missing = record(
        1,
        "pwm.evidence.recorded",
        json!({"evidenceId":"e", "privacyClass":"LOW"}),
    );
    missing.author_key_id = "key:other".into();
    assert_eq!(
        engine.apply(&missing).unwrap_err().code,
        SemanticErrorCode::AuthorizationMissing
    );

    let mut wrong_scope = missing.clone();
    wrong_scope.author_key_id = "key:self".into();
    wrong_scope.principal_scope = "person:other".into();
    assert_eq!(
        engine.apply(&wrong_scope).unwrap_err().code,
        SemanticErrorCode::AuthorizationScopeMismatch
    );

    let denied = record(
        1,
        "pwm.evidence.recorded",
        json!({"evidenceId":"e", "privacyClass":"LOW"}),
    );
    assert_eq!(
        engine.apply(&denied).unwrap_err().code,
        SemanticErrorCode::AuthorizationOperationDenied
    );
    assert_eq!(engine.state().last_log_sequence, Some(0));
}

#[test]
fn lifecycle_privacy_declassification_and_query_are_deterministic() {
    let mut records = vec![
        genesis(&["*"]),
        record(
            1,
            "pwm.evidence.recorded",
            json!({"evidenceId":"e:1", "privacyClass":"SENSITIVE", "value":"source"}),
        ),
        record(2, "pwm.policy.recorded", json!({"policyId":"policy:proof"})),
    ];
    records.extend(accepted_model_records(
        3,
        "m:1",
        json!({"aggregate":"tea", "secret":"medical"}),
    ));
    records.extend([
        record(6, "pwm.declassification.approved", json!({
            "declassificationId":"d:1", "modelId":"m:1", "outputPrivacyClass":"PERSONAL",
            "releasedFields":["aggregate"], "policyRef":"policy:proof"
        })),
        record(7, "pwm.query.authorized", json!({
            "authorityId":"a:1", "principalId":"person:self", "recipientId":"local:test", "purpose":"research",
            "allowedSubjects":["person:self"], "allowedFamilies":["pwm.preference"], "allowedFields":["aggregate"],
            "worldId":"world:actual", "maxPrivacyClass":"PERSONAL", "validFromNs":0, "validToNs":100
        })),
    ]);
    let state = SemanticEngine::reduce(records.iter()).unwrap();
    assert_eq!(
        state.models["m:1"].effective_privacy_class,
        PrivacyClass::Sensitive
    );
    let query = SemanticQuery {
        authority_id: "a:1".into(),
        principal_id: "person:self".into(),
        recipient_id: "local:test".into(),
        purpose: "research".into(),
        subjects: ["person:self".into()].into(),
        families: BTreeSet::new(),
        fields: ["aggregate".into()].into(),
        world_id: ACTUAL_WORLD.into(),
        max_privacy_class: PrivacyClass::Personal,
        at_ns: 50,
        include_disputed: false,
    };
    let result = SemanticEngine::from_state(state.clone())
        .query(&query)
        .unwrap();
    assert_eq!(result.models.len(), 1);
    assert_eq!(
        result.models[0].state,
        [("aggregate".into(), json!("tea"))].into()
    );
    let first = serde_json::to_string(&state).unwrap();
    let second = serde_json::to_string(&SemanticEngine::reduce(records.iter()).unwrap()).unwrap();
    assert_eq!(first, second);
}

#[test]
fn family_kind_possible_world_and_dependency_cycles_fail_closed() {
    let family_records = [
        genesis(&["*"]),
        record(
            1,
            "pwm.family.registered",
            json!({"familyId":"pwm.preference", "allowedKinds":["SELF"]}),
        ),
        record(
            2,
            "pwm.evidence.recorded",
            json!({"evidenceId":"e:1", "privacyClass":"LOW"}),
        ),
        record(
            3,
            "pwm.model.proposed",
            json!({
                "modelId":"bad", "familyId":"pwm.preference", "kind":"WORLD", "subjectIds":["place:kitchen"],
                "perspective":"person:self", "privacyClass":"LOW", "evidenceRefs":["e:1"]
            }),
        ),
    ];
    assert_eq!(
        SemanticEngine::reduce(family_records.iter())
            .unwrap_err()
            .code,
        SemanticErrorCode::FamilyKindNotAllowed
    );

    let actual_world = [
        genesis(&["*"]),
        record(
            1,
            "pwm.evidence.recorded",
            json!({"evidenceId":"e:1", "privacyClass":"LOW"}),
        ),
        record(
            2,
            "pwm.model.proposed",
            json!({
                "modelId":"bad-world", "familyId":"future", "kind":"POSSIBLE_WORLD", "subjectIds":["person:self"],
                "perspective":"person:self", "worldId":"world:actual", "parentWorldId":"world:actual", "privacyClass":"LOW"
            }),
        ),
    ];
    assert_eq!(
        SemanticEngine::reduce(actual_world.iter())
            .unwrap_err()
            .code,
        SemanticErrorCode::PossibleWorldScopeViolation
    );

    let mut cycle = vec![
        genesis(&["*"]),
        record(
            1,
            "pwm.evidence.recorded",
            json!({"evidenceId":"e:1", "privacyClass":"LOW"}),
        ),
    ];
    cycle.extend(accepted_model_records(2, "m:a", json!({"v":"a"})));
    cycle.extend(accepted_model_records(5, "m:b", json!({"v":"b"})));
    cycle.push(record(8, "pwm.topology.edge-added", json!({"edgeId":"a-b", "sourceModelId":"m:a", "edgeType":"DEPENDS_ON", "targetModelId":"m:b", "privacyClass":"LOW"})));
    cycle.push(record(9, "pwm.topology.edge-added", json!({"edgeId":"b-a", "sourceModelId":"m:b", "edgeType":"DEPENDS_ON", "targetModelId":"m:a", "privacyClass":"LOW"})));
    let mut engine = SemanticEngine::new();
    for item in &cycle[..9] {
        engine.apply(item).unwrap();
    }
    assert_eq!(
        engine.apply(&cycle[9]).unwrap_err().code,
        SemanticErrorCode::DependencyCycle
    );
    assert_eq!(
        engine.state().topology.keys().cloned().collect::<Vec<_>>(),
        ["a-b"]
    );
}

#[test]
fn hpl_binding_projection_and_revocation_are_enforced() {
    let records = [
        genesis(&["*"]),
        record(
            1,
            "hpl.projection.requested",
            json!({
                "requestId":"r:1", "principalId":"person:self", "recipientId":"robot:7", "purpose":"delivery",
                "requestedFields":["navigation.zone"], "maxPrivacyClass":"LOW", "atNs":10
            }),
        ),
        record(
            2,
            "hpl.projection.authorized",
            json!({
                "requestId":"r:1", "authorityId":"a:hpl", "principalId":"person:self", "recipientId":"robot:7", "purpose":"delivery",
                "allowedSubjects":[], "allowedFamilies":[], "allowedFields":["navigation.zone"], "worldId":"world:actual",
                "maxPrivacyClass":"LOW", "validFromNs":0, "validToNs":100
            }),
        ),
        record(
            3,
            "hpl.projection.issued",
            json!({
                "projectionId":"p:1", "requestId":"r:1", "authorityId":"a:hpl", "fields":{"navigation.zone":"entry"},
                "fieldPrivacy":{"navigation.zone":"LOW"}, "issuedAtNs":20, "expiresAtNs":90
            }),
        ),
        record(4, "hpl.projection.revoked", json!({"projectionId":"p:1"})),
    ];
    let state = SemanticEngine::reduce(records.iter()).unwrap();
    assert_eq!(
        state.hpl_projections["p:1"].revoked_at_log_sequence,
        Some(4)
    );

    let mut wrong = records[..2].to_vec();
    wrong.push(record(2, "hpl.projection.authorized", json!({
        "requestId":"r:1", "authorityId":"a:bad", "principalId":"person:self", "recipientId":"robot:8", "purpose":"delivery",
        "allowedSubjects":[], "allowedFamilies":[], "allowedFields":["navigation.zone"], "worldId":"world:actual",
        "maxPrivacyClass":"LOW", "validFromNs":0, "validToNs":100
    })));
    assert_eq!(
        SemanticEngine::reduce(wrong.iter()).unwrap_err().code,
        SemanticErrorCode::AuthorityBindingMismatch
    );
}

#[test]
fn canonical_envelope_and_cli_json_are_strict() {
    let malformed = OwnedVerifiedRecord {
        schema_version: "1.0.0".into(),
        event_kind: "pwm.genesis".into(),
        author_key_id: "key:self".into(),
        principal_scope: "person:self".into(),
        log_sequence: 0,
        payload_cbor: vec![0xa0],
        event_body_cid: None,
        parent_event_cids: Vec::new(),
    };
    assert_eq!(
        SemanticEngine::reduce([&malformed]).unwrap_err().code,
        SemanticErrorCode::PayloadEnvelopeInvalid
    );

    let input = json!({"records":[genesis(&["*"])], "query":null}).to_string();
    let first = evaluate_json(&input).unwrap();
    let second = evaluate_json(&input).unwrap();
    assert_eq!(first, second);
    assert!(first.contains("\"lastLogSequence\":0"));
}

#[test]
fn dispute_revoke_and_update_preserve_history() {
    let mut records = vec![
        genesis(&["*"]),
        record(
            1,
            "pwm.evidence.recorded",
            json!({"evidenceId":"e:1", "privacyClass":"LOW"}),
        ),
    ];
    records.extend(accepted_model_records(2, "m:1", json!({"v":1})));
    records.push(record(5, "pwm.model.disputed", json!({"modelId":"m:1"})));
    records.push(record(6, "pwm.model.proposed", json!({
        "modelId":"m:2", "familyId":"pwm.preference", "kind":"SELF", "subjectIds":["person:self"],
        "perspective":"person:self", "state":{"v":2}, "privacyClass":"LOW", "evidenceRefs":["e:1"], "previousModelId":"m:1"
    })));
    records.push(record(
        7,
        "pwm.model.reviewed",
        json!({"modelId":"m:2", "decision":"ACCEPT", "reviewer":"person:self"}),
    ));
    records.push(record(8, "pwm.model.updated", json!({"modelId":"m:2"})));
    records.push(record(9, "pwm.model.revoked", json!({"modelId":"m:2"})));
    let state = SemanticEngine::reduce(records.iter()).unwrap();
    assert!(state.models.is_empty());
    assert_eq!(
        state.historical_models["m:1"].status,
        ModelStatus::Superseded
    );
    assert_eq!(state.historical_models["m:2"].status, ModelStatus::Revoked);
}
