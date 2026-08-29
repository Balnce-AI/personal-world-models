---
status: PROPOSED
version: 0.1.0
---
# Personal World Model Core Specification

## 1. Definition

A **Personal World Model (PWM)** is a sovereign, temporally versioned, provenance-bearing, access-controlled semantic model of a person, the entities and environments relevant to them, the person's relationships to those entities, and the person's observations, beliefs, preferences, commitments, capabilities, intentions, policies, and uncertainty over time.

A PWM is not defined by a storage engine or neural architecture.

## 2. Required distinctions

An implementation MUST preserve the difference among:

- observation;
- assertion;
- accepted operational fact;
- belief;
- inference;
- prediction;
- dispute;
- preference;
- policy;
- intent;
- commitment;
- capability;
- event;
- current materialized state.

A user correction MUST NOT require deletion of the provenance that explains why an earlier state existed, unless the underlying privacy policy requires cryptographic erasure or physical deletion.

## 3. Temporal assertion

An assertion is modeled as:

\[
a = \langle s,p,o,t_v,t_r,\sigma,c,\rho,\pi \rangle
\]

where:

- `s,p,o`: subject, predicate, object;
- `t_v`: valid time in the modeled world;
- `t_r`: record time;
- `σ`: epistemic status;
- `c`: confidence/evidence vector;
- `ρ`: privacy/policy classification;
- `π`: provenance reference.

## 4. Materialized world state

Let `L≤t` be the authorized provenance/event closure available at time `t` and `q` a materialization profile:

\[
W_t = M(L_{\le t},q,\Pi,\Omega)
\]

The materializer SHOULD be deterministic for a pinned schema version, policy profile, and conflict-resolution profile.

## 5. Minimal public object classes

- `Entity`
- `Relation`
- `Assertion`
- `NormativeObject`
- `IntentionalObject`
- `ProvenanceReference`
- `ProjectionReference`

Profiles MAY extend these classes. Extension MUST NOT silently change the meaning of existing fields.

## 6. Canonical/private implementation note

The public reference implementation uses conventional content hashes and event identifiers. A production Balnce implementation may map objects to the richer UOR/PLOG substrate. The public profile MUST NOT be misrepresented as the complete private UOR/PLOG semantics.
