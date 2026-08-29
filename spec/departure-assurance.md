---
status: PROPOSED
version: 0.1.0
---
# Departure Assurance

Do not equate "session ended" with "recipient forgot."

| Level | Evidence | Permitted claim |
|---|---|---|
| `KEY_INVALIDATED` | decryption/revocation key invalidated | future normal access is disabled |
| `DEACTIVATED` | runtime no longer loads/uses artifact | runtime access stopped |
| `PROTOCOL_DEPARTURE` | signed recipient acknowledgement | cooperative cleanup was requested/acknowledged |
| `ATTESTED_DEPARTURE` | evidence from attested runtime executing cleanup profile | stronger environment-specific cleanup evidence |
| `VERIFIED_DEPARTURE` | declared hardware/cryptographic proof profile validated | narrow proof within stated assumptions |
| `UNVERIFIED` | no trustworthy evidence | persistence risk remains |

No level proves that a human observer, opaque external logger, earlier derived inference, screenshot, or undisclosed copy has disappeared unless that property is explicitly covered by the proof profile.
