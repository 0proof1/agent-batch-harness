# Platform Support

Agent Batch Harness supports Python 3.11+ on Linux, macOS, and Windows.

| Concern | Linux/macOS | Windows |
|---|---|---|
| Manifest lock | `flock` | `msvcrt` byte-range lock |
| Shell runner | `sh -c` | Python delegates the command string to `COMSPEC` |
| Timeout isolation | new process session/group | new process group |
| Timeout cleanup | `SIGTERM`, then `SIGKILL` | `taskkill /T /F` |

Shell and verifier command strings are platform-specific. Prefer a portable
executable or Python entry point when the same workflow must run everywhere.
Paths in TSV files should use project-relative syntax accepted by Python's
`pathlib`; do not embed user home directories.

CI covers Python 3.11-3.13 on Linux and Python 3.12 on macOS and Windows. Agent
CLIs invoked by a runner remain external prerequisites and may have narrower
platform support than Agent Batch Harness itself.
