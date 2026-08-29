---
status: PROPOSED
version: 0.1.0
---
# Arranger Specification

## Canonical distinction

**Arranger is an artifact, not the transport envelope.**

In Balnce canon the **Hyperframe** is the polymorphic carrier/envelope. An Arranger is a signed, scoped, revocable crystallized transfer artifact carried by that envelope. This public profile preserves that distinction even when Hyperframe is not implemented by a third party.

## Payload classes

An Arranger MAY carry or reference one or more typed payloads:

- `CONTEXT`
- `IDENTITY_PREDICATE`
- `AUTHORITY`
- `POLICY`
- `SPATIAL`
- `PROCEDURE`
- `BEHAVIOR`
- `MODEL_ADAPTER`
- `DISTILLED_MODEL`
- `SESSION_STATE`
- `PROOF`

The payload class is not the Arranger's identity.

## Required bindings

- issuer;
- recipient;
- purpose/task;
- capabilities;
- forbidden capabilities;
- runtime/model compatibility where applicable;
- hardware/environment binding where applicable;
- issued/expiry time;
- nonce/anti-replay;
- revocation handle;
- provenance references;
- learning-return policy;
- departure requirement.

## Crystallization

The canonical five-rung Crystallization Gradient remains:

**interpreted → contextual → programmatic → adapter → distilled**

An Arranger can package outputs from one or more rungs. Deployment form (for example, embedded execution) is not automatically a new rung.
