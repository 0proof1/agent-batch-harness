# Security Audit Record

## 2026-07-15 0.1.0a2 Candidate

- Runtime dependency count: 0
- Unit and concurrency tests: 39 passed locally
- Release policy and version-consistency scan: passed
- Archive boundary scan: wheel and sdist passed
- Fresh-wheel installation and CLI smoke test: passed
- Installed package and metadata versions: both `0.1.0a2`
- macOS and Windows results: pending GitHub Actions

## 2026-07-12 Local Candidate

- Runtime dependency count: 0
- Release policy scan: passed
- Archive boundary scan: wheel and sdist passed
- Private-key, GitHub-token, AWS-key, and absolute-home-path patterns: 0
- Trust model: local commands run with the user's permissions; no sandbox claim
- POSIX lock contention and process-tree timeout cleanup: passed locally
- Windows lock, shell, and process-tree paths: configured for Windows CI

Build tooling and GitHub Actions remain subject to automated dependency updates.
Repeat this review for every release candidate and after any dependency change.
