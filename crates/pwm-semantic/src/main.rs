use std::{env, fs, process::ExitCode};

fn main() -> ExitCode {
    let arguments: Vec<_> = env::args().skip(1).collect();
    match arguments.as_slice() {
        [command] if command == "identify" => {
            println!(
                "{}",
                serde_json::to_string(&pwm_semantic::identify()).expect("identify is serializable")
            );
            ExitCode::SUCCESS
        }
        [command, flag, path] if command == "evaluate-records" && flag == "--input" => {
            let input = match fs::read_to_string(path) {
                Ok(input) => input,
                Err(error) => {
                    eprintln!("{error}");
                    return ExitCode::from(2);
                }
            };
            let input = match serde_json::from_str(input.as_str()) {
                Ok(input) => input,
                Err(error) => {
                    eprintln!("{error}");
                    return ExitCode::from(2);
                }
            };
            let output = pwm_semantic::evaluate_conformance(input);
            let accepted = output.decision == "ACCEPT";
            println!(
                "{}",
                serde_json::to_string(&output).expect("conformance output is serializable")
            );
            if accepted {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(1)
            }
        }
        [command, flag, path] if command == "evaluate" && flag == "--bundle" => {
            let input = match fs::read_to_string(path) {
                Ok(input) => input,
                Err(error) => {
                    eprintln!("{error}");
                    return ExitCode::from(2);
                }
            };
            let output = pwm_semantic::evaluate_signed_source_json(&input);
            let accepted = output.decision == "ACCEPT";
            let value = serde_json::to_value(output).expect("conformance output is serializable");
            println!(
                "{}",
                serde_json::to_string(&value).expect("JSON value is serializable")
            );
            if accepted {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(1)
            }
        }
        _ => {
            eprintln!(
                "usage: pwm-semantic identify | evaluate --bundle SOURCE.json | evaluate-records --input SOURCE.json"
            );
            ExitCode::from(2)
        }
    }
}
