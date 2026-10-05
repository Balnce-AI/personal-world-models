use std::collections::BTreeMap;

use pwm_canonical::{EventBodyCid, PayloadCid, Value, encode};
use pwm_crypto::SigningKey;
use pwm_event::{
    DagError, EventBody, KeyRegistry, MemoryDag, SchemaRegistry, SignedEvent,
    deterministic_topological_order,
};

fn payload(text: &str) -> (PayloadCid, Vec<u8>) {
    let bytes = encode(&Value::Map(vec![(
        "message".into(),
        Value::Text(text.into()),
    )]))
    .unwrap();
    (PayloadCid::from_canonical_bytes(&bytes), bytes)
}

#[allow(clippy::too_many_arguments)]
fn event(
    signer: &SigningKey,
    key_id: &str,
    scope: &str,
    kind: &str,
    sequence: u64,
    parents: Vec<EventBodyCid>,
    payload_cid: PayloadCid,
    event_time: i64,
) -> SignedEvent {
    SignedEvent::sign(
        EventBody::new(
            "1.0.0",
            kind,
            key_id,
            scope,
            parents,
            sequence,
            event_time,
            payload_cid,
        )
        .unwrap(),
        signer,
    )
    .unwrap()
}

fn registry() -> SchemaRegistry {
    SchemaRegistry::new([
        ("pwm.genesis", "1.0.0"),
        ("evidence.observed", "1.0.0"),
        ("evidence.merged", "1.0.0"),
    ])
    .unwrap()
}

#[test]
fn rejects_unsorted_and_duplicate_parents() {
    let (payload_cid, _) = payload("x");
    let low = EventBodyCid::from_digest([1; 32]);
    let high = EventBodyCid::from_digest([2; 32]);

    assert_eq!(
        EventBody::new(
            "1.0.0",
            "evidence.observed",
            "key:a",
            "person:test",
            vec![high, low],
            1,
            0,
            payload_cid,
        ),
        Err(DagError::ParentsNotSorted)
    );
    assert_eq!(
        EventBody::new(
            "1.0.0",
            "evidence.observed",
            "key:a",
            "person:test",
            vec![low, low],
            1,
            0,
            payload_cid,
        ),
        Err(DagError::DuplicateParent)
    );
}

#[test]
fn validates_genesis_branch_merge_and_deterministic_replay() {
    let author_a = SigningKey::from_seed([1; 32]);
    let author_b = SigningKey::from_seed([2; 32]);
    let appender = SigningKey::from_seed([3; 32]);
    let mut keys = KeyRegistry::new();
    keys.activate("key:a", author_a.public_key(), 0).unwrap();
    keys.activate("key:b", author_b.public_key(), 0).unwrap();
    let schemas = registry();
    let mut dag = MemoryDag::new("append:local", appender.public_key());

    let (gen_payload_cid, gen_payload) = payload("genesis");
    let genesis = event(
        &author_a,
        "key:a",
        "person:test",
        "pwm.genesis",
        0,
        vec![],
        gen_payload_cid,
        100,
    );
    dag.append(&genesis, &gen_payload, 1_000, &keys, &schemas, &appender)
        .unwrap();

    let (left_payload_cid, left_payload) = payload("left");
    let left = event(
        &author_a,
        "key:a",
        "person:test",
        "evidence.observed",
        1,
        vec![genesis.body_cid],
        left_payload_cid,
        -500,
    );
    dag.append(&left, &left_payload, 1_001, &keys, &schemas, &appender)
        .unwrap();

    let (right_payload_cid, right_payload) = payload("right");
    let right = event(
        &author_b,
        "key:b",
        "person:test",
        "evidence.observed",
        0,
        vec![genesis.body_cid],
        right_payload_cid,
        999_999,
    );
    dag.append(&right, &right_payload, 1_002, &keys, &schemas, &appender)
        .unwrap();

    let mut merge_parents = vec![left.body_cid, right.body_cid];
    merge_parents.sort();
    let (merge_payload_cid, merge_payload) = payload("merge");
    let merge = event(
        &author_a,
        "key:a",
        "person:test",
        "evidence.merged",
        2,
        merge_parents,
        merge_payload_cid,
        0,
    );
    let receipt = dag
        .append(&merge, &merge_payload, 1_003, &keys, &schemas, &appender)
        .unwrap();

    receipt.verify(&appender.public_key()).unwrap();
    assert_eq!(dag.frontier(), vec![merge.body_cid]);
    let replay = dag.replay().unwrap();
    assert_eq!(replay.first(), Some(&genesis.body_cid));
    assert_eq!(replay.last(), Some(&merge.body_cid));
    assert!(replay.iter().position(|id| id == &left.body_cid).unwrap() < 3);
    assert!(replay.iter().position(|id| id == &right.body_cid).unwrap() < 3);

    let verified = dag.verified_replay().unwrap();
    let verified_cids: Vec<_> = verified
        .iter()
        .map(|record| record.event().body_cid)
        .collect();
    assert_eq!(verified_cids, replay);
    assert_eq!(verified.first().unwrap().payload_bytes(), gen_payload);
    assert_eq!(verified.last().unwrap().payload_bytes(), merge_payload);
    assert_eq!(verified.last().unwrap().receipt(), &receipt);
}

#[test]
fn retained_payload_is_isolated_from_caller_mutation() {
    let author = SigningKey::from_seed([31; 32]);
    let appender = SigningKey::from_seed([32; 32]);
    let mut keys = KeyRegistry::new();
    keys.activate("key:a", author.public_key(), 0).unwrap();
    let schemas = registry();
    let mut dag = MemoryDag::new("append:local", appender.public_key());
    let (payload_cid, mut bytes) = payload("retained");
    let original = bytes.clone();
    let genesis = event(
        &author,
        "key:a",
        "person:test",
        "pwm.genesis",
        0,
        vec![],
        payload_cid,
        0,
    );

    dag.append(&genesis, &bytes, 1, &keys, &schemas, &appender)
        .unwrap();
    bytes.fill(0);

    let record = dag.verified_record(&genesis.body_cid).unwrap();
    assert_eq!(record.event(), &genesis);
    assert_eq!(record.payload_bytes(), original);
}

#[test]
fn rejects_missing_parent_cross_scope_bad_sequence_and_bad_genesis() {
    let author = SigningKey::from_seed([4; 32]);
    let appender = SigningKey::from_seed([5; 32]);
    let mut keys = KeyRegistry::new();
    keys.activate("key:a", author.public_key(), 0).unwrap();
    let schemas = registry();
    let mut dag = MemoryDag::new("append:local", appender.public_key());
    let (payload_cid, bytes) = payload("bad");

    let genesis = event(
        &author,
        "key:a",
        "person:test",
        "pwm.genesis",
        0,
        vec![],
        payload_cid,
        0,
    );
    dag.append(&genesis, &bytes, 1, &keys, &schemas, &appender)
        .unwrap();

    let missing = event(
        &author,
        "key:a",
        "person:test",
        "evidence.observed",
        1,
        vec![EventBodyCid::from_digest([8; 32])],
        payload_cid,
        0,
    );
    assert_eq!(
        dag.append(&missing, &bytes, 2, &keys, &schemas, &appender),
        Err(DagError::MissingParent)
    );

    let malformed = event(
        &author,
        "key:a",
        "person:test",
        "pwm.genesis",
        1,
        vec![],
        payload_cid,
        0,
    );
    assert_eq!(
        dag.append(&malformed, &bytes, 2, &keys, &schemas, &appender),
        Err(DagError::MalformedGenesis)
    );

    let bad_sequence = event(
        &author,
        "key:a",
        "person:test",
        "evidence.observed",
        2,
        vec![genesis.body_cid],
        payload_cid,
        0,
    );
    assert_eq!(
        dag.append(&bad_sequence, &bytes, 2, &keys, &schemas, &appender),
        Err(DagError::InvalidAuthorSequence)
    );

    let other_genesis = event(
        &author,
        "key:a",
        "person:other",
        "pwm.genesis",
        0,
        vec![],
        payload_cid,
        0,
    );
    dag.append(&other_genesis, &bytes, 2, &keys, &schemas, &appender)
        .unwrap();
    let cross_scope = event(
        &author,
        "key:a",
        "person:test",
        "evidence.observed",
        1,
        vec![other_genesis.body_cid],
        payload_cid,
        0,
    );
    assert_eq!(
        dag.append(&cross_scope, &bytes, 3, &keys, &schemas, &appender),
        Err(DagError::CrossScopeParent)
    );
}

#[test]
fn revocation_uses_append_order_not_author_time() {
    let author = SigningKey::from_seed([6; 32]);
    let appender = SigningKey::from_seed([7; 32]);
    let mut keys = KeyRegistry::new();
    keys.activate("key:a", author.public_key(), 0).unwrap();
    let schemas = registry();
    let mut dag = MemoryDag::new("append:local", appender.public_key());
    let (gen_cid, gen_bytes) = payload("genesis");
    let genesis = event(
        &author,
        "key:a",
        "person:test",
        "pwm.genesis",
        0,
        vec![],
        gen_cid,
        10_000,
    );
    let accepted = dag
        .append(&genesis, &gen_bytes, 100, &keys, &schemas, &appender)
        .unwrap();

    keys.revoke("key:a", 1).unwrap();
    accepted.verify(&appender.public_key()).unwrap();
    let (late_cid, late_bytes) = payload("late");
    let late = event(
        &author,
        "key:a",
        "person:test",
        "evidence.observed",
        1,
        vec![genesis.body_cid],
        late_cid,
        -9_999_999,
    );
    assert_eq!(
        dag.append(&late, &late_bytes, 101, &keys, &schemas, &appender),
        Err(DagError::KeyRevoked)
    );
}

#[test]
fn detects_cycles_in_corrupt_graph_and_uses_cid_tie_break() {
    let a = EventBodyCid::from_digest([1; 32]);
    let b = EventBodyCid::from_digest([2; 32]);
    let c = EventBodyCid::from_digest([3; 32]);
    let cyclic = BTreeMap::from([(a, vec![b]), (b, vec![a])]);
    assert_eq!(
        deterministic_topological_order(&cyclic),
        Err(DagError::CycleDetected)
    );

    let valid = BTreeMap::from([(c, vec![a, b]), (b, vec![]), (a, vec![])]);
    assert_eq!(
        deterministic_topological_order(&valid).unwrap(),
        vec![a, b, c]
    );
}
