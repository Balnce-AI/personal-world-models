# Extensions

Status: `EXPERIMENTAL` ecosystem guidance.

1. Choose exactly the required public protocol roles.
2. Allocate a collision-resistant namespace and semantic version.
3. Declare exact semantics, operations, limits, external dependencies and custody.
4. Implement `CREATED -> STARTED -> STOPPED`; do not silently restart or operate outside `STARTED`.
5. Fail unknown semantics closed with `UnknownSemanticsError`.
6. Require authorization references at disclosure, transfer, tool, promotion and actuation boundaries.
7. Emit event drafts through `EventSink`; never mutate `PWMState` or treat model output as accepted state.
8. Add synthetic contract, threat and portability tests. Never publish personal data fixtures.

Extensions must not import private Balnce packages, claim production compatibility from structural typing, reinterpret normative fields, or make capability discovery confer authority. Start with `templates/adapter/`, record consequential choices using `templates/adr/`, and benchmark claims using `templates/benchmark/`.

Compatibility is scoped to the descriptor version and tested semantics. Major semantic changes require a new capability version. Security fixes may remove unsafe behavior without preserving compatibility.
