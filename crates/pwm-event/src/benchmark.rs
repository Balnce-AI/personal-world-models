//! Reproducible synthetic performance measurement for the public DAG profile.

use std::time::Instant;

use pwm_canonical::{PayloadCid, Value, encode};
use pwm_crypto::SigningKey;
use serde::Serialize;

use crate::{
    DagError, EventBody, GENESIS_EVENT_KIND, KeyRegistry, MemoryDag, SchemaRegistry, SignedEvent,
};

#[derive(Debug, Serialize)]
pub struct DagBenchmarkReport {
    pub profile: &'static str,
    pub environment: BenchmarkEnvironment,
    pub cases: Vec<DagBenchmarkCase>,
    pub limitations: Vec<&'static str>,
}

#[derive(Debug, Serialize)]
pub struct BenchmarkEnvironment {
    pub operating_system: &'static str,
    pub architecture: &'static str,
    pub rust_version: String,
    pub build_profile: &'static str,
}

#[derive(Debug, Serialize)]
pub struct DagBenchmarkCase {
    pub events: usize,
    pub replayed_events: usize,
    pub append_nanoseconds: u128,
    pub replay_nanoseconds: u128,
    pub append_events_per_second: u64,
    pub replay_events_per_second: u64,
}

pub fn run_dag_benchmark(sizes: &[usize]) -> Result<DagBenchmarkReport, DagError> {
    let mut cases = Vec::with_capacity(sizes.len());
    for &size in sizes {
        cases.push(run_case(size)?);
    }
    Ok(DagBenchmarkReport {
        profile: "pwm-public-provenance-v1",
        environment: BenchmarkEnvironment {
            operating_system: std::env::consts::OS,
            architecture: std::env::consts::ARCH,
            rust_version: rust_version(),
            build_profile: if cfg!(debug_assertions) {
                "debug"
            } else {
                "release"
            },
        },
        cases,
        limitations: vec![
            "Synthetic single-author linear DAG; not a production workload.",
            "Wall-clock timing includes canonical encoding and Ed25519 signing and verification.",
            "Results are descriptive for the recorded environment and are not a performance guarantee.",
        ],
    })
}

fn run_case(size: usize) -> Result<DagBenchmarkCase, DagError> {
    let author = SigningKey::from_seed([17; 32]);
    let appender = SigningKey::from_seed([29; 32]);
    let mut keys = KeyRegistry::new();
    keys.activate("benchmark-author", author.public_key(), 0)?;
    let schemas = SchemaRegistry::new([(GENESIS_EVENT_KIND, "1"), ("pwm.benchmark", "1")])?;
    let mut dag = MemoryDag::new("benchmark-appender", appender.public_key());
    let mut parent = None;

    let append_started = Instant::now();
    for index in 0..size {
        let payload = encode(&Value::Map(vec![(
            "index".into(),
            Value::Unsigned(index as u64),
        )]))
        .map_err(DagError::Canonical)?;
        let body = EventBody::new(
            "1",
            if index == 0 {
                GENESIS_EVENT_KIND
            } else {
                "pwm.benchmark"
            },
            "benchmark-author",
            "benchmark-scope",
            parent.into_iter().collect(),
            index as u64,
            index as i64,
            PayloadCid::from_canonical_bytes(&payload),
        )?;
        let event = SignedEvent::sign(body, &author)?;
        dag.append(&event, &payload, index as i64, &keys, &schemas, &appender)?;
        parent = Some(event.body_cid);
    }
    let append_nanoseconds = append_started.elapsed().as_nanos();

    let replay_started = Instant::now();
    let replayed_events = dag.replay()?.len();
    let replay_nanoseconds = replay_started.elapsed().as_nanos();

    Ok(DagBenchmarkCase {
        events: size,
        replayed_events,
        append_nanoseconds,
        replay_nanoseconds,
        append_events_per_second: rate(size, append_nanoseconds),
        replay_events_per_second: rate(size, replay_nanoseconds),
    })
}

fn rate(events: usize, nanoseconds: u128) -> u64 {
    if nanoseconds == 0 {
        return 0;
    }
    ((events as u128 * 1_000_000_000) / nanoseconds) as u64
}

fn rust_version() -> String {
    std::process::Command::new("rustc")
        .arg("--version")
        .output()
        .ok()
        .filter(|output| output.status.success())
        .and_then(|output| String::from_utf8(output.stdout).ok())
        .map(|version| version.trim().to_owned())
        .unwrap_or_else(|| "unknown".into())
}
