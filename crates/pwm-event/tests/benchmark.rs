use pwm_event::benchmark::run_dag_benchmark;

#[test]
fn benchmark_reports_validation_and_replay_for_each_requested_size() {
    let report = run_dag_benchmark(&[10, 25]).unwrap();

    assert_eq!(report.profile, "pwm-public-provenance-v1");
    assert_eq!(report.cases.len(), 2);
    assert_eq!(report.cases[0].events, 10);
    assert_eq!(report.cases[0].replayed_events, 10);
    assert!(report.cases[0].append_nanoseconds > 0);
    assert!(report.cases[0].replay_nanoseconds > 0);
    assert_eq!(report.cases[1].events, 25);
    assert_eq!(report.cases[1].replayed_events, 25);
}
