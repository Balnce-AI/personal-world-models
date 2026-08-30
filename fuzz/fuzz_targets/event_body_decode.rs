#![no_main]

use libfuzzer_sys::fuzz_target;
use pwm_event::EventBody;

fuzz_target!(|data: &[u8]| {
    if let Ok(body) = EventBody::from_canonical_bytes(data) {
        assert_eq!(body.canonical_bytes().expect("accepted body encodes"), data);
    }
});
