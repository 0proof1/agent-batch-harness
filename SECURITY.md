# Security Policy

Report vulnerabilities through the repository host's private security advisory
channel. Do not open a public issue containing credentials, private prompts,
agent logs, or sensitive project content.

## Trust Model

Agent Batch Harness executes local agent and shell commands with the current user's
permissions. It is not a sandbox. Prompt files, runner commands, verifier
commands, work directories, and item manifests must therefore be trusted.

Manifest locking protects status-file consistency. It does not isolate worker
processes, prevent malicious commands, or protect shared output paths. Use
disjoint shard outputs and an external sandbox when inputs or commands are not
trusted.

Timed-out runners are started in a separate process group. Agent Batch Harness terminates
that group on POSIX and uses `taskkill /T /F` on Windows. External services and
detached processes remain outside this guarantee.

Security fixes target the latest release and the current main branch.
