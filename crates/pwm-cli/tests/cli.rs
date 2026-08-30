use std::process::Command;

#[test]
fn emits_verifies_and_replays_public_vectors() {
    let directory = tempfile::tempdir().unwrap();
    let bundle = directory.path().join("vectors.json");
    let executable = env!("CARGO_BIN_EXE_pwm");

    let emit = Command::new(executable)
        .args(["vectors", "emit", "--output"])
        .arg(&bundle)
        .output()
        .unwrap();
    assert!(
        emit.status.success(),
        "{}",
        String::from_utf8_lossy(&emit.stderr)
    );

    let verify = Command::new(executable)
        .args(["event", "verify", "--bundle"])
        .arg(&bundle)
        .output()
        .unwrap();
    assert!(
        verify.status.success(),
        "{}",
        String::from_utf8_lossy(&verify.stderr)
    );
    assert_eq!(
        String::from_utf8(verify.stdout).unwrap().trim(),
        "verified 4 events"
    );

    let replay = Command::new(executable)
        .args(["event", "replay", "--bundle"])
        .arg(&bundle)
        .output()
        .unwrap();
    assert!(
        replay.status.success(),
        "{}",
        String::from_utf8_lossy(&replay.stderr)
    );
    let order: Vec<String> = serde_json::from_slice(&replay.stdout).unwrap();
    assert_eq!(order.len(), 4);
}
