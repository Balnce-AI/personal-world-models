#![no_main]

use libfuzzer_sys::fuzz_target;
use pwm_canonical::{decode_canonical, encode};

fuzz_target!(|data: &[u8]| {
    if let Ok(value) = decode_canonical(data) {
        assert_eq!(encode(&value).expect("accepted values encode"), data);
    }
});
