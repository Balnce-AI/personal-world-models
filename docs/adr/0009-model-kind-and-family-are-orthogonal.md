# ADR 0009: Model Kind And Family Are Orthogonal

**Status:** `PROPOSED`

## Context
Domain labels such as preference, health, and trust do not alone identify whether a record models self, another actor, a relationship, world state, a meta-model, or a hypothetical world.

## Decision
Every model declares both a family and one of `SELF`, `OTHER`, `RELATIONSHIP`, `WORLD`, `META`, or `POSSIBLE_WORLD`. The family registry declares allowed combinations, cardinality, perspective, target, and required-state constraints.

## Alternatives
A single taxonomy hierarchy was rejected because it collapses perspective and domain. Fully unconstrained composition was rejected because invalid combinations become interoperable accidents.

## Consequences
Families retain limited polymorphism, and extensions can add constraints without changing the core model record.
