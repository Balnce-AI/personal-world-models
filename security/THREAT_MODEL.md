# Threat Model

## Protected assets
- canonical world-model state and keys;
- projection eligibility/policy;
- derived artifacts and behavioral models;
- authority/delegation state;
- spatial privacy;
- learning-return integrity;
- recipient/runtime identity;
- provenance and receipts.

## Adversaries
- malicious or compromised recipient;
- malicious edge/cloud provider;
- malicious OEM/service provider;
- prompt/content injection attacker;
- replay attacker;
- model-inversion attacker;
- sensor-poisoning source;
- compromised sovereign device;
- side-channel attacker.

## Required controls
- least-disclosure projection;
- signed recipient/purpose/TTL bindings;
- anti-replay nonces;
- deny-by-default capability authorization;
- runtime/model compatibility checks;
- attestation where it materially changes trust;
- no direct foreign mutation of canonical PWM;
- departure assurance vocabulary matched to actual evidence;
- local safety veto for physical actuation.
