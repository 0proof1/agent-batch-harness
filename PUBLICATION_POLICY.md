# Publication Policy

Shardflow publishes reusable source, tests, synthetic examples, role prompts,
skills, and documentation under the MIT License.

Do not publish runner logs, real project prompts, generated evidence, secrets,
personal information, private URLs, proprietary source material, or absolute
internal paths. Example data must be synthetic and independently redistributable.

A release candidate must pass `python3 tools/release_check.py`, the full test
suite, package build, wheel installation smoke test, and a manual review of the
complete Git history.
