# Dependency Policy

Agent Batch Harness keeps a zero-runtime-dependency core. A proposed dependency must solve
a cross-platform or security problem that the standard library cannot address
cleanly, and its license, maintenance, supply-chain risk, and installation cost
must be documented in the pull request.

Development and CI dependencies should remain minimal. Dependabot tracks Python
build tooling and GitHub Actions. Supported Python versions are those listed in
CI; support is removed only in a documented minor or major release.
