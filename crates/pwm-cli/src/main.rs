use std::{fs, path::PathBuf, process::ExitCode};

use clap::{Args, Parser, Subcommand};
use pwm_canonical::{AppendReceiptBodyCid, EventBodyCid, PayloadCid, Value, encode};
use pwm_crypto::{PublicKey, SIGNATURE_ALGORITHM, Signature, SigningKey};
use pwm_event::{
    AppendReceiptBody, EventBody, KeyRegistry, MemoryDag, SchemaRegistry, SignedAppendReceipt,
    SignedEvent,
};
use serde::{Deserialize, Serialize};

#[derive(Parser)]
#[command(
    name = "pwm",
    version,
    about = "PWM public interoperability profile tools"
)]
struct Cli {
    #[command(subcommand)]
    command: TopLevel,
}

#[derive(Subcommand)]
enum TopLevel {
    Event(EventCommand),
    Vectors(VectorCommand),
}

#[derive(Args)]
struct EventCommand {
    #[command(subcommand)]
    command: EventAction,
}

#[derive(Subcommand)]
enum EventAction {
    Verify(BundleArgument),
    Replay(BundleArgument),
}

#[derive(Args)]
struct VectorCommand {
    #[command(subcommand)]
    command: VectorAction,
}

#[derive(Subcommand)]
enum VectorAction {
    Emit {
        #[arg(long)]
        output: PathBuf,
    },
}

#[derive(Args)]
struct BundleArgument {
    #[arg(long)]
    bundle: PathBuf,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct VectorBundle {
    profile: String,
    appender_key_id: String,
    appender_public_key_hex: String,
    author_keys: Vec<KeyVector>,
    schemas: Vec<SchemaVector>,
    records: Vec<RecordVector>,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct KeyVector {
    key_id: String,
    public_key_hex: String,
    active_from_log_sequence: u64,
    revoked_at_log_sequence: Option<u64>,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct SchemaVector {
    event_kind: String,
    schema_version: String,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct RecordVector {
    body_cbor_hex: String,
    body_cid: String,
    event_signature_hex: String,
    payload_cbor_hex: String,
    receipt_body_cbor_hex: String,
    receipt_cid: String,
    receipt_signature_hex: String,
}

fn main() -> ExitCode {
    match run(Cli::parse()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        }
    }
}

fn run(cli: Cli) -> Result<(), String> {
    match cli.command {
        TopLevel::Vectors(VectorCommand {
            command: VectorAction::Emit { output },
        }) => {
            let json = serde_json::to_vec_pretty(&generate_vectors()?).map_err(display)?;
            fs::write(output, [json, b"\n".to_vec()].concat()).map_err(display)
        }
        TopLevel::Event(EventCommand {
            command: EventAction::Verify(arguments),
        }) => {
            let (_, count) = load_bundle(&arguments.bundle)?;
            println!("verified {count} events");
            Ok(())
        }
        TopLevel::Event(EventCommand {
            command: EventAction::Replay(arguments),
        }) => {
            let (dag, _) = load_bundle(&arguments.bundle)?;
            let order: Vec<_> = dag
                .replay()
                .map_err(display)?
                .into_iter()
                .map(|cid| cid.to_string())
                .collect();
            println!("{}", serde_json::to_string_pretty(&order).map_err(display)?);
            Ok(())
        }
    }
}

fn generate_vectors() -> Result<VectorBundle, String> {
    let root = SigningKey::from_seed([31; 32]);
    let left = SigningKey::from_seed([32; 32]);
    let right = SigningKey::from_seed([33; 32]);
    let appender = SigningKey::from_seed([34; 32]);
    let key_specs = [
        ("key:root", &root),
        ("key:left", &left),
        ("key:right", &right),
    ];
    let mut keys = KeyRegistry::new();
    let mut author_keys = Vec::new();
    for (key_id, signer) in key_specs {
        keys.activate(key_id, signer.public_key(), 0)
            .map_err(display)?;
        author_keys.push(KeyVector {
            key_id: key_id.into(),
            public_key_hex: hex::encode(signer.public_key().as_bytes()),
            active_from_log_sequence: 0,
            revoked_at_log_sequence: None,
        });
    }
    let schemas = SchemaRegistry::new([
        ("pwm.genesis", "1.0.0"),
        ("pwm.evidence", "1.0.0"),
        ("pwm.merge", "1.0.0"),
    ])
    .map_err(display)?;
    let mut dag = MemoryDag::new("key:appender", appender.public_key());
    let mut records = Vec::new();

    let (genesis, payload) = make_event(
        "pwm.genesis",
        "key:root",
        vec![],
        0,
        1_725_000_000_000_000_000,
        Value::Map(vec![("fixture".into(), Value::Text("wave-01".into()))]),
        &root,
    )?;
    records.push(append_vector(
        &mut dag,
        genesis.clone(),
        payload,
        1_725_000_000_000_000_100,
        &keys,
        &schemas,
        &appender,
    )?);
    keys.revoke("key:root", 1).map_err(display)?;
    author_keys[0].revoked_at_log_sequence = Some(1);
    let root_v2 = SigningKey::from_seed([35; 32]);
    keys.activate("key:root:v2", root_v2.public_key(), 1)
        .map_err(display)?;
    author_keys.push(KeyVector {
        key_id: "key:root:v2".into(),
        public_key_hex: hex::encode(root_v2.public_key().as_bytes()),
        active_from_log_sequence: 1,
        revoked_at_log_sequence: None,
    });
    let (left_event, payload) = make_event(
        "pwm.evidence",
        "key:left",
        vec![genesis.body_cid],
        0,
        1_725_000_000_000_000_010,
        Value::Text("left".into()),
        &left,
    )?;
    records.push(append_vector(
        &mut dag,
        left_event.clone(),
        payload,
        1_725_000_000_000_000_200,
        &keys,
        &schemas,
        &appender,
    )?);
    let (right_event, payload) = make_event(
        "pwm.evidence",
        "key:right",
        vec![genesis.body_cid],
        0,
        1_725_000_000_000_000_005,
        Value::Text("right".into()),
        &right,
    )?;
    records.push(append_vector(
        &mut dag,
        right_event.clone(),
        payload,
        1_725_000_000_000_000_300,
        &keys,
        &schemas,
        &appender,
    )?);
    let mut merge_parents = vec![left_event.body_cid, right_event.body_cid];
    merge_parents.sort_by(|a, b| a.as_bytes().cmp(b.as_bytes()));
    let (merge, payload) = make_event(
        "pwm.merge",
        "key:root:v2",
        merge_parents,
        0,
        1_725_000_000_000_000_001,
        Value::Text("merged".into()),
        &root_v2,
    )?;
    records.push(append_vector(
        &mut dag,
        merge,
        payload,
        1_725_000_000_000_000_400,
        &keys,
        &schemas,
        &appender,
    )?);

    Ok(VectorBundle {
        profile: "pwm-public-provenance-v1".into(),
        appender_key_id: "key:appender".into(),
        appender_public_key_hex: hex::encode(appender.public_key().as_bytes()),
        author_keys,
        schemas: vec![
            SchemaVector {
                event_kind: "pwm.genesis".into(),
                schema_version: "1.0.0".into(),
            },
            SchemaVector {
                event_kind: "pwm.evidence".into(),
                schema_version: "1.0.0".into(),
            },
            SchemaVector {
                event_kind: "pwm.merge".into(),
                schema_version: "1.0.0".into(),
            },
        ],
        records,
    })
}

fn make_event(
    event_kind: &str,
    key_id: &str,
    parents: Vec<EventBodyCid>,
    sequence: u64,
    event_time: i64,
    payload: Value,
    signer: &SigningKey,
) -> Result<(SignedEvent, Vec<u8>), String> {
    let payload = encode(&payload).map_err(display)?;
    let body = EventBody::new(
        "1.0.0",
        event_kind,
        key_id,
        "person:public-vector",
        parents,
        sequence,
        event_time,
        PayloadCid::from_canonical_bytes(&payload),
    )
    .map_err(display)?;
    Ok((SignedEvent::sign(body, signer).map_err(display)?, payload))
}

fn append_vector(
    dag: &mut MemoryDag,
    event: SignedEvent,
    payload: Vec<u8>,
    ingestion_time: i64,
    keys: &KeyRegistry,
    schemas: &SchemaRegistry,
    appender: &SigningKey,
) -> Result<RecordVector, String> {
    let receipt = dag
        .append(&event, &payload, ingestion_time, keys, schemas, appender)
        .map_err(display)?;
    Ok(RecordVector {
        body_cbor_hex: hex::encode(event.body.canonical_bytes().map_err(display)?),
        body_cid: event.body_cid.to_string(),
        event_signature_hex: hex::encode(event.signature.as_bytes()),
        payload_cbor_hex: hex::encode(payload),
        receipt_body_cbor_hex: hex::encode(
            receipt.receipt_body.canonical_bytes().map_err(display)?,
        ),
        receipt_cid: receipt.receipt_cid.to_string(),
        receipt_signature_hex: hex::encode(receipt.signature.as_bytes()),
    })
}

fn load_bundle(path: &PathBuf) -> Result<(MemoryDag, usize), String> {
    let bytes = fs::read(path).map_err(display)?;
    let bundle: VectorBundle = serde_json::from_slice(&bytes).map_err(display)?;
    if bundle.profile != "pwm-public-provenance-v1" {
        return Err("unsupported vector profile".into());
    }
    let appender_public_key = public_key(&bundle.appender_public_key_hex)?;
    let mut keys = KeyRegistry::new();
    for key in &bundle.author_keys {
        keys.activate(
            &key.key_id,
            public_key(&key.public_key_hex)?,
            key.active_from_log_sequence,
        )
        .map_err(display)?;
    }
    for key in &bundle.author_keys {
        if let Some(revoked_at_log_sequence) = key.revoked_at_log_sequence {
            keys.revoke(&key.key_id, revoked_at_log_sequence)
                .map_err(display)?;
        }
    }
    let schemas = SchemaRegistry::new(
        bundle
            .schemas
            .iter()
            .map(|schema| (&schema.event_kind, &schema.schema_version)),
    )
    .map_err(display)?;
    let mut dag = MemoryDag::new(&bundle.appender_key_id, appender_public_key);
    for record in &bundle.records {
        let body_bytes = hex::decode(&record.body_cbor_hex).map_err(display)?;
        let body = EventBody::from_canonical_bytes(&body_bytes).map_err(display)?;
        let body_cid: EventBodyCid = record.body_cid.parse().map_err(display)?;
        let event = SignedEvent {
            body,
            body_cid,
            signature_algorithm: SIGNATURE_ALGORITHM.into(),
            signature: Signature::from_bytes(hex_array(&record.event_signature_hex)?),
        };
        let receipt_bytes = hex::decode(&record.receipt_body_cbor_hex).map_err(display)?;
        let receipt = SignedAppendReceipt {
            receipt_body: AppendReceiptBody::from_canonical_bytes(&receipt_bytes)
                .map_err(display)?,
            receipt_cid: record
                .receipt_cid
                .parse::<AppendReceiptBodyCid>()
                .map_err(display)?,
            signature_algorithm: SIGNATURE_ALGORITHM.into(),
            signature: Signature::from_bytes(hex_array(&record.receipt_signature_hex)?),
        };
        let payload = hex::decode(&record.payload_cbor_hex).map_err(display)?;
        dag.import_verified(event, &payload, receipt, &keys, &schemas)
            .map_err(display)?;
    }
    let count = bundle.records.len();
    Ok((dag, count))
}

fn public_key(value: &str) -> Result<PublicKey, String> {
    PublicKey::from_bytes(hex_array(value)?).map_err(display)
}

fn hex_array<const N: usize>(value: &str) -> Result<[u8; N], String> {
    hex::decode(value)
        .map_err(display)?
        .try_into()
        .map_err(|_| format!("expected {N} bytes"))
}

fn display(error: impl std::fmt::Display) -> String {
    error.to_string()
}
