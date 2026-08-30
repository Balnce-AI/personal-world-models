use pwm_event::benchmark::run_dag_benchmark;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let report = run_dag_benchmark(&[1_000, 10_000, 100_000])?;
    println!("{}", serde_json::to_string_pretty(&report)?);
    Ok(())
}
