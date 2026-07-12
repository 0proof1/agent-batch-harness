# Open-Source Readiness

Agent Batch Harness is an alpha reference harness, not a production
orchestrator or a security boundary.

The local release candidate has an MIT publication boundary, synthetic
examples, unit and concurrency tests, a cross-platform CI matrix, package smoke
tests, and a documented trust model. A runner-only success is recorded as
`succeeded`; only a configured verifier can produce `verified`.

Readiness that cannot be established from repository files remains open:

- installation feedback from unrelated users;
- real recovery experience after interrupted external runners;
- repeated macOS and Windows release results;
- compatibility evidence for additional agent CLIs;
- multiple maintainers and public governance history.

Until that evidence exists, releases remain `0.x` alpha and should be described
as small, inspectable workflow infrastructure rather than production-grade
verification.
