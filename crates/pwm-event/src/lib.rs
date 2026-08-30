//! Signed causal event DAG for the public PWM provenance profile.
//!
//! This crate is a bounded interoperability implementation. It is not the
//! private production PLOG, a world-model materializer, or an authority engine.

pub mod benchmark;

use std::{
    collections::{BTreeMap, BTreeSet, HashMap, HashSet},
    path::Path,
};

use pwm_canonical::{
    AppendReceiptBodyCid, CanonicalError, EventBodyCid, KeyStatusFrontierCid, PayloadCid, Value,
    decode_canonical, encode,
};
use pwm_crypto::{PublicKey, SIGNATURE_ALGORITHM, Signature, SigningKey, VerifyError};
use rusqlite::{Connection, params};
use thiserror::Error;

pub const GENESIS_EVENT_KIND: &str = "pwm.genesis";

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EventBody {
    pub schema_version: String,
    pub event_kind: String,
    pub author_key_id: String,
    pub principal_scope: String,
    pub parent_event_cids: Vec<EventBodyCid>,
    pub author_sequence: u64,
    pub event_time: i64,
    pub payload_cid: PayloadCid,
}

impl EventBody {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        schema_version: impl Into<String>,
        event_kind: impl Into<String>,
        author_key_id: impl Into<String>,
        principal_scope: impl Into<String>,
        parent_event_cids: Vec<EventBodyCid>,
        author_sequence: u64,
        event_time: i64,
        payload_cid: PayloadCid,
    ) -> Result<Self, DagError> {
        if parent_event_cids.windows(2).any(|pair| pair[0] > pair[1]) {
            return Err(DagError::ParentsNotSorted);
        }
        if parent_event_cids.windows(2).any(|pair| pair[0] == pair[1]) {
            return Err(DagError::DuplicateParent);
        }
        Ok(Self {
            schema_version: schema_version.into(),
            event_kind: event_kind.into(),
            author_key_id: author_key_id.into(),
            principal_scope: principal_scope.into(),
            parent_event_cids,
            author_sequence,
            event_time,
            payload_cid,
        })
    }

    pub fn canonical_bytes(&self) -> Result<Vec<u8>, DagError> {
        encode(&self.as_value()).map_err(DagError::Canonical)
    }

    pub fn from_canonical_bytes(bytes: &[u8]) -> Result<Self, DagError> {
        let mut fields = value_map(decode_canonical(bytes).map_err(DagError::Canonical)?)?;
        let body = Self::new(
            take_text(&mut fields, "schema_version")?,
            take_text(&mut fields, "event_kind")?,
            take_text(&mut fields, "author_key_id")?,
            take_text(&mut fields, "principal_scope")?,
            take_array(&mut fields, "parent_event_cids")?
                .into_iter()
                .map(|value| {
                    EventBodyCid::from_bytes(&value_bytes(value)?)
                        .map_err(|_| DagError::MalformedRecord)
                })
                .collect::<Result<Vec<_>, _>>()?,
            take_unsigned(&mut fields, "author_sequence")?,
            take_integer(&mut fields, "event_time")?,
            PayloadCid::from_bytes(&take_bytes(&mut fields, "payload_cid")?)
                .map_err(|_| DagError::MalformedRecord)?,
        )?;
        ensure_empty(fields)?;
        Ok(body)
    }

    fn as_value(&self) -> Value {
        Value::Map(vec![
            (
                "author_key_id".into(),
                Value::Text(self.author_key_id.clone()),
            ),
            (
                "author_sequence".into(),
                Value::Unsigned(self.author_sequence),
            ),
            ("event_kind".into(), Value::Text(self.event_kind.clone())),
            ("event_time".into(), integer_value(self.event_time)),
            (
                "parent_event_cids".into(),
                Value::Array(
                    self.parent_event_cids
                        .iter()
                        .map(|cid| Value::Bytes(cid.as_bytes().to_vec()))
                        .collect(),
                ),
            ),
            (
                "payload_cid".into(),
                Value::Bytes(self.payload_cid.as_bytes().to_vec()),
            ),
            (
                "principal_scope".into(),
                Value::Text(self.principal_scope.clone()),
            ),
            (
                "schema_version".into(),
                Value::Text(self.schema_version.clone()),
            ),
        ])
    }
}

fn integer_value(value: i64) -> Value {
    if value >= 0 {
        Value::Unsigned(value as u64)
    } else {
        Value::Negative(value)
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SignedEvent {
    pub body: EventBody,
    pub body_cid: EventBodyCid,
    pub signature_algorithm: String,
    pub signature: Signature,
}

impl SignedEvent {
    pub fn sign(body: EventBody, signer: &SigningKey) -> Result<Self, DagError> {
        let body_cid = EventBodyCid::from_canonical_bytes(&body.canonical_bytes()?);
        let signature = signer.sign_event_body(&body_cid);
        Ok(Self {
            body,
            body_cid,
            signature_algorithm: SIGNATURE_ALGORITHM.into(),
            signature,
        })
    }

    pub fn verify_integrity(&self, public_key: &PublicKey) -> Result<(), DagError> {
        if self.signature_algorithm != SIGNATURE_ALGORITHM {
            return Err(DagError::UnsupportedSignatureAlgorithm);
        }
        let expected = EventBodyCid::from_canonical_bytes(&self.body.canonical_bytes()?);
        if expected != self.body_cid {
            return Err(DagError::BodyCidMismatch);
        }
        public_key
            .verify_event_body(&self.body_cid, &self.signature)
            .map_err(DagError::Signature)
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AppendReceiptBody {
    pub body_cid: EventBodyCid,
    pub ingestion_time: i64,
    pub key_status_frontier_cid: KeyStatusFrontierCid,
    pub log_sequence: u64,
    pub appender_key_id: String,
}

impl AppendReceiptBody {
    pub fn canonical_bytes(&self) -> Result<Vec<u8>, DagError> {
        encode(&Value::Map(vec![
            (
                "appender_key_id".into(),
                Value::Text(self.appender_key_id.clone()),
            ),
            (
                "body_cid".into(),
                Value::Bytes(self.body_cid.as_bytes().to_vec()),
            ),
            ("ingestion_time".into(), integer_value(self.ingestion_time)),
            (
                "key_status_frontier_cid".into(),
                Value::Bytes(self.key_status_frontier_cid.as_bytes().to_vec()),
            ),
            ("log_sequence".into(), Value::Unsigned(self.log_sequence)),
        ]))
        .map_err(DagError::Canonical)
    }

    pub fn from_canonical_bytes(bytes: &[u8]) -> Result<Self, DagError> {
        let mut fields = value_map(decode_canonical(bytes).map_err(DagError::Canonical)?)?;
        let body = Self {
            body_cid: EventBodyCid::from_bytes(&take_bytes(&mut fields, "body_cid")?)
                .map_err(|_| DagError::MalformedRecord)?,
            ingestion_time: take_integer(&mut fields, "ingestion_time")?,
            key_status_frontier_cid: KeyStatusFrontierCid::from_bytes(&take_bytes(
                &mut fields,
                "key_status_frontier_cid",
            )?)
            .map_err(|_| DagError::MalformedRecord)?,
            log_sequence: take_unsigned(&mut fields, "log_sequence")?,
            appender_key_id: take_text(&mut fields, "appender_key_id")?,
        };
        ensure_empty(fields)?;
        Ok(body)
    }
}

fn value_map(value: Value) -> Result<BTreeMap<String, Value>, DagError> {
    match value {
        Value::Map(entries) => Ok(entries.into_iter().collect()),
        _ => Err(DagError::MalformedRecord),
    }
}

fn take_value(fields: &mut BTreeMap<String, Value>, name: &str) -> Result<Value, DagError> {
    fields.remove(name).ok_or(DagError::MalformedRecord)
}

fn take_text(fields: &mut BTreeMap<String, Value>, name: &str) -> Result<String, DagError> {
    match take_value(fields, name)? {
        Value::Text(value) => Ok(value),
        _ => Err(DagError::MalformedRecord),
    }
}

fn take_bytes(fields: &mut BTreeMap<String, Value>, name: &str) -> Result<Vec<u8>, DagError> {
    value_bytes(take_value(fields, name)?)
}

fn value_bytes(value: Value) -> Result<Vec<u8>, DagError> {
    match value {
        Value::Bytes(value) => Ok(value),
        _ => Err(DagError::MalformedRecord),
    }
}

fn take_array(fields: &mut BTreeMap<String, Value>, name: &str) -> Result<Vec<Value>, DagError> {
    match take_value(fields, name)? {
        Value::Array(value) => Ok(value),
        _ => Err(DagError::MalformedRecord),
    }
}

fn take_unsigned(fields: &mut BTreeMap<String, Value>, name: &str) -> Result<u64, DagError> {
    match take_value(fields, name)? {
        Value::Unsigned(value) => Ok(value),
        _ => Err(DagError::MalformedRecord),
    }
}

fn take_integer(fields: &mut BTreeMap<String, Value>, name: &str) -> Result<i64, DagError> {
    match take_value(fields, name)? {
        Value::Unsigned(value) => i64::try_from(value).map_err(|_| DagError::MalformedRecord),
        Value::Negative(value) => Ok(value),
        _ => Err(DagError::MalformedRecord),
    }
}

fn ensure_empty(fields: BTreeMap<String, Value>) -> Result<(), DagError> {
    if fields.is_empty() {
        Ok(())
    } else {
        Err(DagError::MalformedRecord)
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SignedAppendReceipt {
    pub receipt_body: AppendReceiptBody,
    pub receipt_cid: AppendReceiptBodyCid,
    pub signature_algorithm: String,
    pub signature: Signature,
}

impl SignedAppendReceipt {
    fn sign(body: AppendReceiptBody, signer: &SigningKey) -> Result<Self, DagError> {
        let receipt_cid = AppendReceiptBodyCid::from_canonical_bytes(&body.canonical_bytes()?);
        let signature = signer.sign_append_receipt(&receipt_cid);
        Ok(Self {
            receipt_body: body,
            receipt_cid,
            signature_algorithm: SIGNATURE_ALGORITHM.into(),
            signature,
        })
    }

    pub fn verify(&self, appender_key: &PublicKey) -> Result<(), DagError> {
        if self.signature_algorithm != SIGNATURE_ALGORITHM {
            return Err(DagError::UnsupportedSignatureAlgorithm);
        }
        let expected =
            AppendReceiptBodyCid::from_canonical_bytes(&self.receipt_body.canonical_bytes()?);
        if expected != self.receipt_cid {
            return Err(DagError::ReceiptCidMismatch);
        }
        appender_key
            .verify_append_receipt(&self.receipt_cid, &self.signature)
            .map_err(DagError::Signature)
    }
}

#[derive(Clone, Debug)]
struct KeyRecord {
    public_key: PublicKey,
    active_from_log_sequence: u64,
    revoked_at_log_sequence: Option<u64>,
}

#[derive(Clone, Debug, Default)]
pub struct KeyRegistry {
    current: BTreeMap<String, KeyRecord>,
    snapshots: HashMap<KeyStatusFrontierCid, BTreeMap<String, KeyRecord>>,
}

impl KeyRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn activate(
        &mut self,
        key_id: impl Into<String>,
        public_key: PublicKey,
        active_from_log_sequence: u64,
    ) -> Result<KeyStatusFrontierCid, DagError> {
        let key_id = key_id.into();
        if self.current.contains_key(&key_id) {
            return Err(DagError::DuplicateKey);
        }
        self.current.insert(
            key_id,
            KeyRecord {
                public_key,
                active_from_log_sequence,
                revoked_at_log_sequence: None,
            },
        );
        self.capture_frontier()
    }

    pub fn revoke(
        &mut self,
        key_id: &str,
        revoked_at_log_sequence: u64,
    ) -> Result<KeyStatusFrontierCid, DagError> {
        let record = self.current.get_mut(key_id).ok_or(DagError::UnknownKey)?;
        if record.revoked_at_log_sequence.is_some()
            || revoked_at_log_sequence < record.active_from_log_sequence
        {
            return Err(DagError::InvalidKeyTransition);
        }
        record.revoked_at_log_sequence = Some(revoked_at_log_sequence);
        self.capture_frontier()
    }

    pub fn current_frontier(&self) -> Result<KeyStatusFrontierCid, DagError> {
        self.frontier_for(&self.current)
    }

    pub fn resolve_current(&self, key_id: &str, log_sequence: u64) -> Result<&PublicKey, DagError> {
        resolve_record(&self.current, key_id, log_sequence)
    }

    pub fn resolve_at(
        &self,
        frontier: &KeyStatusFrontierCid,
        key_id: &str,
        log_sequence: u64,
    ) -> Result<&PublicKey, DagError> {
        let snapshot = self
            .snapshots
            .get(frontier)
            .ok_or(DagError::UnknownKeyFrontier)?;
        resolve_record(snapshot, key_id, log_sequence)
    }

    fn capture_frontier(&mut self) -> Result<KeyStatusFrontierCid, DagError> {
        let frontier = self.frontier_for(&self.current)?;
        self.snapshots.insert(frontier, self.current.clone());
        Ok(frontier)
    }

    fn frontier_for(
        &self,
        records: &BTreeMap<String, KeyRecord>,
    ) -> Result<KeyStatusFrontierCid, DagError> {
        let values = records
            .iter()
            .map(|(key_id, record)| {
                Value::Map(vec![
                    ("key_id".into(), Value::Text(key_id.clone())),
                    (
                        "public_key".into(),
                        Value::Bytes(record.public_key.as_bytes().to_vec()),
                    ),
                    (
                        "active_from_log_sequence".into(),
                        Value::Unsigned(record.active_from_log_sequence),
                    ),
                    (
                        "revoked_at_log_sequence".into(),
                        record
                            .revoked_at_log_sequence
                            .map(Value::Unsigned)
                            .unwrap_or(Value::Null),
                    ),
                ])
            })
            .collect();
        let bytes = encode(&Value::Array(values)).map_err(DagError::Canonical)?;
        Ok(KeyStatusFrontierCid::from_canonical_bytes(&bytes))
    }
}

fn resolve_record<'a>(
    records: &'a BTreeMap<String, KeyRecord>,
    key_id: &str,
    log_sequence: u64,
) -> Result<&'a PublicKey, DagError> {
    let record = records.get(key_id).ok_or(DagError::UnknownKey)?;
    if log_sequence < record.active_from_log_sequence {
        return Err(DagError::KeyNotActive);
    }
    if record
        .revoked_at_log_sequence
        .is_some_and(|revoked| log_sequence >= revoked)
    {
        return Err(DagError::KeyRevoked);
    }
    Ok(&record.public_key)
}

#[derive(Clone, Debug)]
pub struct SchemaRegistry(BTreeMap<String, String>);

impl SchemaRegistry {
    pub fn new<I, K, V>(entries: I) -> Result<Self, DagError>
    where
        I: IntoIterator<Item = (K, V)>,
        K: Into<String>,
        V: Into<String>,
    {
        let mut registry = BTreeMap::new();
        for (kind, version) in entries {
            if registry.insert(kind.into(), version.into()).is_some() {
                return Err(DagError::DuplicateSchema);
            }
        }
        Ok(Self(registry))
    }

    fn verify(&self, kind: &str, version: &str) -> Result<(), DagError> {
        match self.0.get(kind) {
            Some(expected) if expected == version => Ok(()),
            Some(_) => Err(DagError::SchemaVersionMismatch),
            None => Err(DagError::UnknownSchema),
        }
    }
}

#[derive(Clone)]
struct StoredEvent {
    event: SignedEvent,
    receipt: SignedAppendReceipt,
}

#[derive(Clone)]
pub struct MemoryDag {
    appender_key_id: String,
    appender_public_key: PublicKey,
    events: BTreeMap<EventBodyCid, StoredEvent>,
    genesis_by_scope: HashMap<String, EventBodyCid>,
    author_heads: HashMap<(String, String), (u64, EventBodyCid)>,
    next_log_sequence: u64,
}

impl MemoryDag {
    pub fn new(appender_key_id: impl Into<String>, appender_public_key: PublicKey) -> Self {
        Self {
            appender_key_id: appender_key_id.into(),
            appender_public_key,
            events: BTreeMap::new(),
            genesis_by_scope: HashMap::new(),
            author_heads: HashMap::new(),
            next_log_sequence: 0,
        }
    }

    pub fn append(
        &mut self,
        event: &SignedEvent,
        payload_bytes: &[u8],
        ingestion_time: i64,
        keys: &KeyRegistry,
        schemas: &SchemaRegistry,
        appender_signer: &SigningKey,
    ) -> Result<SignedAppendReceipt, DagError> {
        if appender_signer.public_key() != self.appender_public_key {
            return Err(DagError::WrongAppenderKey);
        }
        decode_canonical(payload_bytes).map_err(DagError::Canonical)?;
        if PayloadCid::from_canonical_bytes(payload_bytes) != event.body.payload_cid {
            return Err(DagError::PayloadCidMismatch);
        }
        if let Some(stored) = self.events.get(&event.body_cid) {
            if &stored.event != event {
                return Err(DagError::RetryMismatch);
            }
            return Ok(stored.receipt.clone());
        }
        schemas.verify(&event.body.event_kind, &event.body.schema_version)?;
        let author_key = keys.resolve_current(&event.body.author_key_id, self.next_log_sequence)?;
        event.verify_integrity(author_key)?;
        self.validate_shape(event)?;
        self.validate_author_sequence(event)?;

        let key_status_frontier_cid = keys.current_frontier()?;
        // Confirm the receipt frontier can resolve the same historical key.
        keys.resolve_at(
            &key_status_frontier_cid,
            &event.body.author_key_id,
            self.next_log_sequence,
        )?;
        let receipt = SignedAppendReceipt::sign(
            AppendReceiptBody {
                body_cid: event.body_cid,
                ingestion_time,
                key_status_frontier_cid,
                log_sequence: self.next_log_sequence,
                appender_key_id: self.appender_key_id.clone(),
            },
            appender_signer,
        )?;
        receipt.verify(&self.appender_public_key)?;

        if event.body.event_kind == GENESIS_EVENT_KIND {
            self.genesis_by_scope
                .insert(event.body.principal_scope.clone(), event.body_cid);
        }
        let author_head = (
            (
                event.body.principal_scope.clone(),
                event.body.author_key_id.clone(),
            ),
            (event.body.author_sequence, event.body_cid),
        );
        self.events.insert(
            event.body_cid,
            StoredEvent {
                event: event.clone(),
                receipt: receipt.clone(),
            },
        );
        self.author_heads.insert(author_head.0, author_head.1);
        self.next_log_sequence = self
            .next_log_sequence
            .checked_add(1)
            .ok_or(DagError::SequenceOverflow)?;
        Ok(receipt)
    }

    fn validate_shape(&self, event: &SignedEvent) -> Result<(), DagError> {
        let is_genesis = event.body.event_kind == GENESIS_EVENT_KIND;
        if is_genesis {
            if !event.body.parent_event_cids.is_empty()
                || event.body.author_sequence != 0
                || self
                    .genesis_by_scope
                    .contains_key(&event.body.principal_scope)
            {
                return Err(DagError::MalformedGenesis);
            }
            return Ok(());
        }
        if event.body.parent_event_cids.is_empty()
            || !self
                .genesis_by_scope
                .contains_key(&event.body.principal_scope)
        {
            return Err(DagError::MalformedGenesis);
        }
        for parent in &event.body.parent_event_cids {
            let stored = self.events.get(parent).ok_or(DagError::MissingParent)?;
            if stored.event.body.principal_scope != event.body.principal_scope {
                return Err(DagError::CrossScopeParent);
            }
            // Existing accepted parents cannot descend from a not-yet-appended CID.
            // Self-reference remains an explicit malformed-input check.
            if *parent == event.body_cid {
                return Err(DagError::CycleDetected);
            }
        }
        Ok(())
    }

    fn validate_author_sequence(&self, event: &SignedEvent) -> Result<(), DagError> {
        let key = (
            event.body.principal_scope.clone(),
            event.body.author_key_id.clone(),
        );
        let prior = self.author_heads.get(&key);
        match prior {
            None if event.body.author_sequence == 0 => Ok(()),
            Some((prior_sequence, prior_cid))
                if event.body.author_sequence == prior_sequence + 1
                    && event.body.parent_event_cids.iter().any(|parent| {
                        *parent == *prior_cid || self.is_ancestor(prior_cid, parent)
                    }) =>
            {
                Ok(())
            }
            _ => Err(DagError::InvalidAuthorSequence),
        }
    }

    fn is_ancestor(&self, sought: &EventBodyCid, start: &EventBodyCid) -> bool {
        let mut pending = vec![*start];
        let mut visited = HashSet::new();
        while let Some(current) = pending.pop() {
            if !visited.insert(current) {
                continue;
            }
            if current == *sought {
                return true;
            }
            if let Some(stored) = self.events.get(&current) {
                pending.extend(stored.event.body.parent_event_cids.iter().copied());
            }
        }
        false
    }

    pub fn frontier(&self) -> Vec<EventBodyCid> {
        let parents: HashSet<_> = self
            .events
            .values()
            .flat_map(|stored| stored.event.body.parent_event_cids.iter().copied())
            .collect();
        self.events
            .keys()
            .filter(|cid| !parents.contains(cid))
            .copied()
            .collect()
    }

    pub fn replay(&self) -> Result<Vec<EventBodyCid>, DagError> {
        deterministic_topological_order(
            &self
                .events
                .iter()
                .map(|(cid, stored)| (*cid, stored.event.body.parent_event_cids.clone()))
                .collect(),
        )
    }

    pub fn receipt(&self, cid: &EventBodyCid) -> Option<&SignedAppendReceipt> {
        self.events.get(cid).map(|stored| &stored.receipt)
    }

    pub fn import_verified(
        &mut self,
        event: SignedEvent,
        payload_bytes: &[u8],
        receipt: SignedAppendReceipt,
        keys: &KeyRegistry,
        schemas: &SchemaRegistry,
    ) -> Result<(), DagError> {
        if receipt.receipt_body.body_cid != event.body_cid
            || receipt.receipt_body.log_sequence != self.next_log_sequence
            || receipt.receipt_body.appender_key_id != self.appender_key_id
        {
            return Err(DagError::CorruptStorage);
        }
        decode_canonical(payload_bytes).map_err(DagError::Canonical)?;
        if PayloadCid::from_canonical_bytes(payload_bytes) != event.body.payload_cid {
            return Err(DagError::PayloadCidMismatch);
        }
        schemas.verify(&event.body.event_kind, &event.body.schema_version)?;
        let author_key = keys.resolve_at(
            &receipt.receipt_body.key_status_frontier_cid,
            &event.body.author_key_id,
            receipt.receipt_body.log_sequence,
        )?;
        event.verify_integrity(author_key)?;
        receipt.verify(&self.appender_public_key)?;
        self.validate_shape(&event)?;
        self.validate_author_sequence(&event)?;
        if event.body.event_kind == GENESIS_EVENT_KIND {
            self.genesis_by_scope
                .insert(event.body.principal_scope.clone(), event.body_cid);
        }
        let author_head = (
            (
                event.body.principal_scope.clone(),
                event.body.author_key_id.clone(),
            ),
            (event.body.author_sequence, event.body_cid),
        );
        self.events
            .insert(event.body_cid, StoredEvent { event, receipt });
        self.author_heads.insert(author_head.0, author_head.1);
        self.next_log_sequence += 1;
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum AppendFault {
    #[default]
    None,
    AfterInsert,
    AbortProcessAfterInsert,
}

pub struct SqliteDag {
    connection: Connection,
    memory: MemoryDag,
}

impl SqliteDag {
    pub fn open(
        path: impl AsRef<Path>,
        appender_key_id: impl Into<String>,
        appender_public_key: PublicKey,
        keys: &KeyRegistry,
        schemas: &SchemaRegistry,
    ) -> Result<Self, DagError> {
        let mut connection = Connection::open(path).map_err(storage_error)?;
        connection
            .execute_batch(
                "PRAGMA foreign_keys = ON;
                 PRAGMA journal_mode = WAL;
                 PRAGMA synchronous = FULL;
                 CREATE TABLE IF NOT EXISTS events (
                   body_cid BLOB PRIMARY KEY,
                   body BLOB NOT NULL,
                   event_signature BLOB NOT NULL,
                   payload BLOB NOT NULL,
                   receipt_body BLOB NOT NULL,
                   receipt_cid BLOB NOT NULL,
                   receipt_signature BLOB NOT NULL,
                   log_sequence INTEGER NOT NULL UNIQUE
                 ) STRICT;
                 CREATE TABLE IF NOT EXISTS parent_edges (
                   child_cid BLOB NOT NULL REFERENCES events(body_cid),
                   parent_cid BLOB NOT NULL REFERENCES events(body_cid),
                   PRIMARY KEY (child_cid, parent_cid)
                 ) STRICT;",
            )
            .map_err(storage_error)?;
        let appender_key_id = appender_key_id.into();
        let mut memory = MemoryDag::new(appender_key_id, appender_public_key);
        let rows = {
            let mut statement = connection
                .prepare(
                    "SELECT body_cid, body, event_signature, payload,
                            receipt_body, receipt_cid, receipt_signature, log_sequence
                     FROM events ORDER BY log_sequence ASC",
                )
                .map_err(storage_error)?;
            let mapped = statement
                .query_map([], |row| {
                    Ok(RawStoredEvent {
                        body_cid: row.get(0)?,
                        body: row.get(1)?,
                        event_signature: row.get(2)?,
                        payload: row.get(3)?,
                        receipt_body: row.get(4)?,
                        receipt_cid: row.get(5)?,
                        receipt_signature: row.get(6)?,
                        log_sequence: row.get(7)?,
                    })
                })
                .map_err(storage_error)?;
            mapped
                .collect::<Result<Vec<_>, _>>()
                .map_err(storage_error)?
        };
        for row in rows {
            let (event, payload, receipt) = row.decode().map_err(|_| DagError::CorruptStorage)?;
            memory
                .import_verified(event, &payload, receipt, keys, schemas)
                .map_err(|_| DagError::CorruptStorage)?;
        }
        // Detect out-of-band edge mutations as well as body mutations.
        verify_parent_edge_table(&mut connection, &memory)?;
        Ok(Self { connection, memory })
    }

    pub fn append(
        &mut self,
        event: &SignedEvent,
        payload_bytes: &[u8],
        ingestion_time: i64,
        keys: &KeyRegistry,
        schemas: &SchemaRegistry,
        appender_signer: &SigningKey,
    ) -> Result<SignedAppendReceipt, DagError> {
        self.append_with_fault(
            event,
            payload_bytes,
            ingestion_time,
            keys,
            schemas,
            appender_signer,
            AppendFault::None,
        )
    }

    #[allow(clippy::too_many_arguments)]
    pub fn append_with_fault(
        &mut self,
        event: &SignedEvent,
        payload_bytes: &[u8],
        ingestion_time: i64,
        keys: &KeyRegistry,
        schemas: &SchemaRegistry,
        appender_signer: &SigningKey,
        fault: AppendFault,
    ) -> Result<SignedAppendReceipt, DagError> {
        let was_stored = self.memory.receipt(&event.body_cid).is_some();
        let mut candidate = self.memory.clone();
        let receipt = candidate.append(
            event,
            payload_bytes,
            ingestion_time,
            keys,
            schemas,
            appender_signer,
        )?;
        if was_stored {
            return Ok(receipt);
        }
        let body = event.body.canonical_bytes()?;
        let receipt_body = receipt.receipt_body.canonical_bytes()?;
        let transaction = self.connection.transaction().map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO events (
                    body_cid, body, event_signature, payload, receipt_body,
                    receipt_cid, receipt_signature, log_sequence
                 ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
                params![
                    event.body_cid.as_bytes().as_slice(),
                    body,
                    event.signature.as_bytes().as_slice(),
                    payload_bytes,
                    receipt_body,
                    receipt.receipt_cid.as_bytes().as_slice(),
                    receipt.signature.as_bytes().as_slice(),
                    i64::try_from(receipt.receipt_body.log_sequence)
                        .map_err(|_| DagError::SequenceOverflow)?,
                ],
            )
            .map_err(storage_error)?;
        if fault == AppendFault::AfterInsert {
            return Err(DagError::SimulatedCrash);
        }
        if fault == AppendFault::AbortProcessAfterInsert {
            std::process::abort();
        }
        for parent in &event.body.parent_event_cids {
            transaction
                .execute(
                    "INSERT INTO parent_edges (child_cid, parent_cid) VALUES (?1, ?2)",
                    params![
                        event.body_cid.as_bytes().as_slice(),
                        parent.as_bytes().as_slice()
                    ],
                )
                .map_err(storage_error)?;
        }
        transaction.commit().map_err(storage_error)?;
        self.memory = candidate;
        Ok(receipt)
    }

    pub fn replay(&self) -> Result<Vec<EventBodyCid>, DagError> {
        self.memory.replay()
    }

    pub fn receipt(&self, cid: &EventBodyCid) -> Option<&SignedAppendReceipt> {
        self.memory.receipt(cid)
    }
}

struct RawStoredEvent {
    body_cid: Vec<u8>,
    body: Vec<u8>,
    event_signature: Vec<u8>,
    payload: Vec<u8>,
    receipt_body: Vec<u8>,
    receipt_cid: Vec<u8>,
    receipt_signature: Vec<u8>,
    log_sequence: i64,
}

impl RawStoredEvent {
    fn decode(self) -> Result<(SignedEvent, Vec<u8>, SignedAppendReceipt), DagError> {
        let body = EventBody::from_canonical_bytes(&self.body)?;
        let body_cid =
            EventBodyCid::from_bytes(&self.body_cid).map_err(|_| DagError::MalformedRecord)?;
        let event = SignedEvent {
            body,
            body_cid,
            signature_algorithm: SIGNATURE_ALGORITHM.into(),
            signature: Signature::from_bytes(array::<64>(&self.event_signature)?),
        };
        let receipt_body = AppendReceiptBody::from_canonical_bytes(&self.receipt_body)?;
        let receipt = SignedAppendReceipt {
            receipt_body,
            receipt_cid: AppendReceiptBodyCid::from_bytes(&self.receipt_cid)
                .map_err(|_| DagError::MalformedRecord)?,
            signature_algorithm: SIGNATURE_ALGORITHM.into(),
            signature: Signature::from_bytes(array::<64>(&self.receipt_signature)?),
        };
        if self.log_sequence < 0 || receipt.receipt_body.log_sequence != self.log_sequence as u64 {
            return Err(DagError::MalformedRecord);
        }
        Ok((event, self.payload, receipt))
    }
}

fn array<const N: usize>(bytes: &[u8]) -> Result<[u8; N], DagError> {
    bytes.try_into().map_err(|_| DagError::MalformedRecord)
}

fn verify_parent_edge_table(
    connection: &mut Connection,
    memory: &MemoryDag,
) -> Result<(), DagError> {
    let expected: BTreeSet<_> = memory
        .events
        .iter()
        .flat_map(|(child, stored)| {
            stored
                .event
                .body
                .parent_event_cids
                .iter()
                .map(move |parent| (child.as_bytes().to_vec(), parent.as_bytes().to_vec()))
        })
        .collect();
    let actual = {
        let mut statement = connection
            .prepare("SELECT child_cid, parent_cid FROM parent_edges")
            .map_err(storage_error)?;
        statement
            .query_map([], |row| {
                Ok((row.get::<_, Vec<u8>>(0)?, row.get::<_, Vec<u8>>(1)?))
            })
            .map_err(storage_error)?
            .collect::<Result<BTreeSet<_>, _>>()
            .map_err(storage_error)?
    };
    if actual != expected {
        return Err(DagError::CorruptStorage);
    }
    Ok(())
}

pub fn deterministic_topological_order(
    graph: &BTreeMap<EventBodyCid, Vec<EventBodyCid>>,
) -> Result<Vec<EventBodyCid>, DagError> {
    let mut indegree: BTreeMap<EventBodyCid, usize> =
        graph.keys().copied().map(|cid| (cid, 0)).collect();
    let mut children: BTreeMap<EventBodyCid, Vec<EventBodyCid>> = BTreeMap::new();
    for (child, parents) in graph {
        for parent in parents {
            if !graph.contains_key(parent) {
                return Err(DagError::MissingParent);
            }
            *indegree.get_mut(child).expect("graph key initialized") += 1;
            children.entry(*parent).or_default().push(*child);
        }
    }
    let mut ready: BTreeSet<EventBodyCid> = indegree
        .iter()
        .filter_map(|(cid, degree)| (*degree == 0).then_some(*cid))
        .collect();
    let mut ordered = Vec::with_capacity(graph.len());
    while let Some(current) = ready.pop_first() {
        ordered.push(current);
        for child in children.get(&current).into_iter().flatten() {
            let degree = indegree.get_mut(child).expect("child belongs to graph");
            *degree -= 1;
            if *degree == 0 {
                ready.insert(*child);
            }
        }
    }
    if ordered.len() != graph.len() {
        return Err(DagError::CycleDetected);
    }
    Ok(ordered)
}

#[derive(Clone, Debug, Error, PartialEq, Eq)]
pub enum DagError {
    #[error("canonical encoding rejected")]
    Canonical(#[source] CanonicalError),
    #[error("parents must be sorted by raw CID bytes")]
    ParentsNotSorted,
    #[error("parent CIDs must be unique")]
    DuplicateParent,
    #[error("event body CID does not match the canonical body")]
    BodyCidMismatch,
    #[error("payload CID does not match the supplied canonical payload")]
    PayloadCidMismatch,
    #[error("append receipt CID does not match the canonical receipt body")]
    ReceiptCidMismatch,
    #[error("signature algorithm is unsupported")]
    UnsupportedSignatureAlgorithm,
    #[error("signature verification failed")]
    Signature(#[source] VerifyError),
    #[error("parent is absent")]
    MissingParent,
    #[error("parent belongs to another principal scope")]
    CrossScopeParent,
    #[error("genesis constraints are not satisfied")]
    MalformedGenesis,
    #[error("cycle detected")]
    CycleDetected,
    #[error("author sequence is not the unique causal successor")]
    InvalidAuthorSequence,
    #[error("key is unknown")]
    UnknownKey,
    #[error("key-status frontier is unknown")]
    UnknownKeyFrontier,
    #[error("key is not active at append order")]
    KeyNotActive,
    #[error("key was revoked before append")]
    KeyRevoked,
    #[error("key transition is invalid")]
    InvalidKeyTransition,
    #[error("key ID already exists")]
    DuplicateKey,
    #[error("schema kind is unknown")]
    UnknownSchema,
    #[error("schema version does not match the registered kind")]
    SchemaVersionMismatch,
    #[error("schema kind is duplicated")]
    DuplicateSchema,
    #[error("appender signer does not match trusted configuration")]
    WrongAppenderKey,
    #[error("log sequence overflow")]
    SequenceOverflow,
    #[error("record does not match the public schema")]
    MalformedRecord,
    #[error("retry content does not match the accepted record")]
    RetryMismatch,
    #[error("durable storage operation failed")]
    Storage,
    #[error("durable storage is corrupt")]
    CorruptStorage,
    #[error("simulated crash before transaction commit")]
    SimulatedCrash,
}

fn storage_error(_: rusqlite::Error) -> DagError {
    DagError::Storage
}
