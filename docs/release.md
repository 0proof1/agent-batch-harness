# Release Process

Releases are prepared locally before any remote action.

1. Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
2. Run `python3 tools/release_check.py` and compile all Python sources.
3. Build wheel and source archives from a clean checkout.
4. Install the wheel into a fresh virtual environment and run `agent-batch --help`.
5. Run `python3 tools/check_artifact.py dist/*` and inspect archives for logs,
   locks, secrets, private prompts, and absolute paths.
6. Generate `dist/sbom.cdx.json` with `tools/generate_sbom.py`.
7. Generate SHA-256 checksums for all release artifacts.
8. Review the complete Git history and publication policy.
9. Only then create a version tag and remote release.

Versions follow semantic versioning. Alpha releases may change file contracts;
stable releases must document migrations for manifest or CLI incompatibilities.

## Repository Rename Handoff

Before publishing `0.1.0a1`, rename the GitHub repository from `shardflow` to
`agent-batch-harness`. After GitHub confirms the rename, update and verify the
local remote:

```bash
git remote set-url origin https://github.com/0proof1/agent-batch-harness.git
git remote -v
```

Do not update `origin` first: the new URL is not usable until the remote rename
has succeeded. Then confirm repository links, issue templates, branch
protection, and trusted-publishing configuration under the new name before
tagging the alpha release.
