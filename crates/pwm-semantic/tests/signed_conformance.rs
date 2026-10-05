use std::collections::BTreeSet;

use pwm_canonical::{Value, encode};
use pwm_semantic::{
    ConformanceCommand, ConformanceInput, OwnedVerifiedRecord, SemanticErrorCode,
    evaluate_conformance,
};
use serde_json::{Value as JsonValue, json};

fn cbor(value: &JsonValue) -> Value {
    match value {
        JsonValue::Null => Value::Null,
        JsonValue::Bool(value) => Value::Bool(*value),
        JsonValue::Number(value) if value.is_u64() => Value::Unsigned(value.as_u64().unwrap()),
        JsonValue::Number(value) => Value::Negative(value.as_i64().unwrap()),
        JsonValue::String(value) => Value::Text(value.clone()),
        JsonValue::Array(values) => Value::Array(values.iter().map(cbor).collect()),
        JsonValue::Object(values) => Value::Map(
            values
                .iter()
                .map(|(key, value)| (key.clone(), cbor(value)))
                .collect(),
        ),
    }
}

fn record(sequence: u64, kind: &str, data: JsonValue) -> OwnedVerifiedRecord {
    let payload = Value::Map(vec![
        (
            "profile".into(),
            Value::Text("pwm-signed-semantics-v1".into()),
        ),
        ("schema_version".into(), Value::Text("1.0.0".into())),
        ("data".into(), cbor(&data)),
        ("valid_from_ns".into(), Value::Unsigned(0)),
        ("valid_to_ns".into(), Value::Null),
    ]);
    OwnedVerifiedRecord {
        schema_version: "1.0.0".into(),
        event_kind: kind.into(),
        author_key_id: "key:root".into(),
        principal_scope: "scope:one".into(),
        log_sequence: sequence,
        payload_cbor: encode(&payload).unwrap(),
        event_body_cid: Some(format!("btest{sequence}")),
        parent_event_cids: if sequence > 0 {
            vec![format!("btest{}", sequence - 1)]
        } else {
            Vec::new()
        },
    }
}

fn genesis(operations: JsonValue, capabilities: JsonValue) -> OwnedVerifiedRecord {
    record(
        0,
        "pwm.genesis",
        json!({
            "scope_id": "scope:one",
            "root_principal_id": "person:root",
            "root_key_id": "key:root",
            "principals": [{"principal_id":"person:root","principal_class":"PERSON"}],
            "grants": [{
                "grant_id":"grant:root", "principal_id":"person:root", "key_id":"key:root",
                "scope_id":"scope:one", "operations":operations, "capabilities":capabilities,
                "grant_class":"ROOT", "valid_from_log_sequence":0, "valid_to_log_sequence":null
            }]
        }),
    )
}

fn reduce(records: Vec<OwnedVerifiedRecord>) -> pwm_semantic::ConformanceOutput {
    evaluate_conformance(ConformanceInput {
        source_id: "case:focused".into(),
        records,
        command: ConformanceCommand {
            operation: "REDUCE".into(),
            evaluation_log_sequence: 1,
            query: None,
            projection_id: None,
            evaluation_id: None,
        },
    })
}

#[test]
fn output_matches_python_envelope_and_byte_wrapper_shape() {
    let output = reduce(vec![
        genesis(json!(["EVIDENCE_CREATE"]), json!(["pwm.evidence.write"])),
        record(
            1,
            "pwm.evidence",
            json!({
                "evidence_id":"e:1", "evidence_kind":"DOCUMENT", "subject_ids":["person:root"],
                "source_uri":null, "content_digest":{"$bytes_hex":"0000000000000000000000000000000000000000000000000000000000000000"},
                "privacy_class":"LOW", "properties":{"title":"source"}
            }),
        ),
    ]);
    let value = serde_json::to_value(&output).unwrap();
    assert_eq!(value["output_version"], "1.0.0");
    assert_eq!(value["profile"], "pwm-signed-semantics-v1");
    assert_eq!(value["decision"], "ACCEPT");
    assert_eq!(value["processed_records"], 2);
    assert_eq!(value["last_committed_log_sequence"], 1);
    assert_eq!(value["result"]["operation"], "REDUCE");
    assert_eq!(value["result"]["state_sha256"].as_str().unwrap().len(), 64);
    assert_eq!(
        value["result"]["value"]["evidence"]["e:1"]["content_digest"],
        json!({"$bytes_hex":"0000000000000000000000000000000000000000000000000000000000000000"})
    );
    assert_eq!(
        value["result"]["value"]["evidence"]["e:1"]["effectivePrivacyClass"],
        "LOW"
    );
    assert_eq!(
        value["result"]["value"]["families"]["pwm.preference"]["allowedKinds"],
        json!(["SELF", "OTHER"])
    );
    assert_eq!(
        value["result"]["value"]["evidence"]["e:1"]["effectivePrivacyClass"],
        "LOW"
    );
    assert_eq!(
        value["result"]["value"]["families"]["pwm.preference"]["allowedKinds"],
        json!(["SELF", "OTHER"])
    );
    assert_eq!(
        value
            .as_object()
            .unwrap()
            .keys()
            .map(String::as_str)
            .collect::<BTreeSet<_>>(),
        BTreeSet::from([
            "decision",
            "implementation",
            "last_committed_log_sequence",
            "output_version",
            "processed_records",
            "profile",
            "result",
            "source_id",
            "state_sha256"
        ])
    );
}

#[test]
fn operation_and_capability_are_normative_and_rejection_is_atomic() {
    let wrong_operation = reduce(vec![
        genesis(json!(["pwm.evidence"]), json!(["pwm.evidence.write"])),
        record(
            1,
            "pwm.evidence",
            json!({
                "evidence_id":"e:1", "evidence_kind":"DOCUMENT", "subject_ids":["person:root"],
                "source_uri":null, "content_digest":{"$bytes_hex":"0000000000000000000000000000000000000000000000000000000000000000"},
                "privacy_class":"LOW", "properties":{}
            }),
        ),
    ]);
    assert_eq!(wrong_operation.decision, "REJECT");
    assert_eq!(wrong_operation.processed_records, 1);
    assert_eq!(wrong_operation.last_committed_log_sequence, Some(0));
    assert_eq!(
        wrong_operation.error.unwrap().code,
        SemanticErrorCode::GrantNotFound
    );

    let missing_capability = reduce(vec![
        genesis(json!(["EVIDENCE_CREATE"]), json!([])),
        record(
            1,
            "pwm.evidence",
            json!({
                "evidence_id":"e:1", "evidence_kind":"DOCUMENT", "subject_ids":["person:root"],
                "source_uri":null, "content_digest":{"$bytes_hex":"0000000000000000000000000000000000000000000000000000000000000000"},
                "privacy_class":"LOW", "properties":{}
            }),
        ),
    ]);
    assert_eq!(
        missing_capability.error.unwrap().code,
        SemanticErrorCode::CapabilityNotGranted
    );
}
