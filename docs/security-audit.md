# Security Audit Record

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
