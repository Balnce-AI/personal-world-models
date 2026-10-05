use pwm_canonical::{PayloadCid, Value, encode};
use pwm_crypto::{Signature, SigningKey};
use pwm_event::{
    AppendFault, DagError, EventBody, KeyRegistry, SchemaRegistry, SignedEvent, SqliteDag,
};
use std::process::Command;

fn fixture() -> (
    SigningKey,
    SigningKey,
    KeyRegistry,
    SchemaRegistry,
    SignedEvent,
    Vec<u8>,
) {
    let author = SigningKey::from_seed([21; 32]);
    let appender = SigningKey::from_seed([22; 32]);
    let mut keys = KeyRegistry::new();
    keys.activate("key:author", author.public_key(), 0).unwrap();
    let schemas = SchemaRegistry::new([("pwm.genesis", "1.0.0")]).unwrap();
    let payload = encode(&Value::Map(vec![(
        "fixture".into(),
        Value::Text("recovery".into()),
    )]))
    .unwrap();
    let event = SignedEvent::sign(
        EventBody::new(
            "1.0.0",
            "pwm.genesis",
            "key:author",
            "person:recovery",
            vec![],
            0,
            5,
            PayloadCid::from_canonical_bytes(&payload),
        )
        .unwrap(),
        &author,
    )
    .unwrap();
    (author, appender, keys, schemas, event, payload)
}

#[test]
fn reopens_and_reverifies_committed_records() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("events.sqlite3");
    let (_, appender, keys, schemas, event, payload) = fixture();
    let receipt = {
        let mut store =
            SqliteDag::open(&path, "append:test", appender.public_key(), &keys, &schemas).unwrap();
        store
            .append(&event, &payload, 10, &keys, &schemas, &appender)
            .unwrap()
    };

    let reopened =
        SqliteDag::open(&path, "append:test", appender.public_key(), &keys, &schemas).unwrap();
    assert_eq!(reopened.replay().unwrap(), vec![event.body_cid]);
    assert_eq!(reopened.receipt(&event.body_cid), Some(&receipt));
    let replay = reopened.verified_replay().unwrap();
    assert_eq!(replay.len(), 1);
    assert_eq!(replay[0].event(), &event);
    assert_eq!(replay[0].payload_bytes(), payload);
    assert_eq!(replay[0].receipt(), &receipt);
}

#[test]
fn interrupted_transaction_recovers_as_no_append() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("events.sqlite3");
    let (_, appender, keys, schemas, event, payload) = fixture();
    {
        let mut store =
            SqliteDag::open(&path, "append:test", appender.public_key(), &keys, &schemas).unwrap();
        assert_eq!(
            store.append_with_fault(
                &event,
                &payload,
                10,
                &keys,
                &schemas,
                &appender,
                AppendFault::AfterInsert,
            ),
            Err(DagError::SimulatedCrash)
        );
    }

    let reopened =
        SqliteDag::open(&path, "append:test", appender.public_key(), &keys, &schemas).unwrap();
    assert!(reopened.replay().unwrap().is_empty());
}

#[test]
fn process_death_inside_transaction_recovers_as_no_append() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("events.sqlite3");
    let status = Command::new(std::env::current_exe().unwrap())
        .args(["--ignored", "--exact", "crash_writer_child"])
        .env("PWM_CRASH_DB", &path)
        .status()
        .unwrap();
    assert!(!status.success());

    let (_, appender, keys, schemas, _, _) = fixture();
    let reopened =
        SqliteDag::open(&path, "append:test", appender.public_key(), &keys, &schemas).unwrap();
    assert!(reopened.replay().unwrap().is_empty());
}

#[test]
#[ignore]
fn crash_writer_child() {
    let path = std::env::var_os("PWM_CRASH_DB").expect("child-only test");
    let (_, appender, keys, schemas, event, payload) = fixture();
    let mut store =
        SqliteDag::open(path, "append:test", appender.public_key(), &keys, &schemas).unwrap();
    let _ = store.append_with_fault(
        &event,
        &payload,
        10,
        &keys,
        &schemas,
        &appender,
        AppendFault::AbortProcessAfterInsert,
    );
    panic!("abort fault returned unexpectedly");
}

#[test]
fn fails_closed_when_committed_bytes_are_corrupted() {
    for mutation in [
        "UPDATE events SET body = X'00'",
        "UPDATE events SET body_cid = X'00'",
        "UPDATE events SET event_signature = X'00'",
        "UPDATE events SET payload = X'00'",
        "UPDATE events SET receipt_body = X'00'",
        "UPDATE events SET receipt_cid = X'00'",
        "UPDATE events SET receipt_signature = X'00'",
        "UPDATE events SET log_sequence = 9",
    ] {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("events.sqlite3");
        let (_, appender, keys, schemas, event, payload) = fixture();
        {
            let mut store =
                SqliteDag::open(&path, "append:test", appender.public_key(), &keys, &schemas)
                    .unwrap();
            store
                .append(&event, &payload, 10, &keys, &schemas, &appender)
                .unwrap();
        }
        let connection = rusqlite::Connection::open(&path).unwrap();
        connection.execute(mutation, []).unwrap();
        drop(connection);

        assert!(
            matches!(
                SqliteDag::open(&path, "append:test", appender.public_key(), &keys, &schemas,),
                Err(DagError::CorruptStorage)
            ),
            "mutation was accepted: {mutation}"
        );
    }
}

#[test]
fn retry_returns_original_receipt_without_allocating_sequence() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("events.sqlite3");
    let (_, appender, keys, schemas, event, payload) = fixture();
    let mut store =
        SqliteDag::open(&path, "append:test", appender.public_key(), &keys, &schemas).unwrap();
    let first = store
        .append(&event, &payload, 10, &keys, &schemas, &appender)
        .unwrap();
    let retry = store
        .append(&event, &payload, 99, &keys, &schemas, &appender)
        .unwrap();

    assert_eq!(first, retry);
    assert_eq!(retry.receipt_body.log_sequence, 0);
}

#[test]
fn retry_rejects_content_that_only_copies_an_accepted_cid() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("events.sqlite3");
    let (_, appender, keys, schemas, event, payload) = fixture();
    let mut store =
        SqliteDag::open(&path, "append:test", appender.public_key(), &keys, &schemas).unwrap();
    store
        .append(&event, &payload, 10, &keys, &schemas, &appender)
        .unwrap();

    let mut altered = event.clone();
    altered.signature = Signature::from_bytes([0; 64]);
    assert_eq!(
        store.append(&altered, &payload, 11, &keys, &schemas, &appender),
        Err(DagError::RetryMismatch)
    );

    let unrelated_payload = encode(&Value::Text("different".into())).unwrap();
    assert_eq!(
        store.append(&event, &unrelated_payload, 11, &keys, &schemas, &appender,),
        Err(DagError::PayloadCidMismatch)
    );
}

#[test]
fn public_storage_error_is_opaque() {
    let directory = tempfile::tempdir().unwrap();
    let (_, appender, keys, schemas, _, _) = fixture();
    let error = match SqliteDag::open(
        directory.path(),
        "append:test",
        appender.public_key(),
        &keys,
        &schemas,
    ) {
        Ok(_) => panic!("opening a directory as SQLite unexpectedly succeeded"),
        Err(error) => error,
    };

    assert_eq!(error, DagError::Storage);
    assert_eq!(format!("{error:?}"), "Storage");
}

#[test]
fn historical_receipts_survive_author_key_rotation_and_revocation() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("events.sqlite3");
    let (old_author, appender, mut keys, _, genesis, genesis_payload) = fixture();
    let schemas =
        SchemaRegistry::new([("pwm.genesis", "1.0.0"), ("pwm.evidence", "1.0.0")]).unwrap();
    let mut store =
        SqliteDag::open(&path, "append:test", appender.public_key(), &keys, &schemas).unwrap();
    store
        .append(&genesis, &genesis_payload, 10, &keys, &schemas, &appender)
        .unwrap();

    keys.revoke("key:author", 1).unwrap();
    let new_author = SigningKey::from_seed([23; 32]);
    keys.activate("key:author:v2", new_author.public_key(), 1)
        .unwrap();
    let payload = encode(&Value::Text("after-rotation".into())).unwrap();
    let child = SignedEvent::sign(
        EventBody::new(
            "1.0.0",
            "pwm.evidence",
            "key:author:v2",
            "person:recovery",
            vec![genesis.body_cid],
            0,
            -5,
            PayloadCid::from_canonical_bytes(&payload),
        )
        .unwrap(),
        &new_author,
    )
    .unwrap();
    store
        .append(&child, &payload, 11, &keys, &schemas, &appender)
        .unwrap();

    let delayed_payload = encode(&Value::Text("delayed".into())).unwrap();
    let delayed_old_key = SignedEvent::sign(
        EventBody::new(
            "1.0.0",
            "pwm.evidence",
            "key:author",
            "person:recovery",
            vec![genesis.body_cid],
            1,
            i64::MIN,
            PayloadCid::from_canonical_bytes(&delayed_payload),
        )
        .unwrap(),
        &old_author,
    )
    .unwrap();
    assert_eq!(
        store.append(
            &delayed_old_key,
            &delayed_payload,
            12,
            &keys,
            &schemas,
            &appender,
        ),
        Err(DagError::KeyRevoked)
    );
    drop(store);

    let reopened =
        SqliteDag::open(&path, "append:test", appender.public_key(), &keys, &schemas).unwrap();
    assert_eq!(
        reopened.replay().unwrap(),
        vec![genesis.body_cid, child.body_cid]
    );
}
