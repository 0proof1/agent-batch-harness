# Agent Batch Harness

<p align="center"><strong>긴 에이전트 작업을 나누고, 모든 실행을 기록하고, 신뢰하기 전에 검증합니다.</strong></p>

<p align="center">
  <a href="README.md">English</a> · <strong>한국어</strong>
</p>

<p align="center"><code>Python 3.11+</code> · <code>Linux</code> · <code>macOS</code> · <code>Windows</code> · <code>MIT</code></p>

Agent Batch Harness는 큰 작업을 여러 shard로 나누어 실행하고 중단된 지점부터 다시
이어갈 수 있게 만드는 작고 투명한 파일 기반 harness입니다.

한 번의 에이전트 실행으로 처리하기에는 너무 크거나 오래 걸리는 작업을
명확한 범위, prompt, 로그, 예상 산출물, 검증 결과가 있는 작업 단위로
바꿉니다. Codex, Claude Code, Gemini CLI, 자체 에이전트 runner 또는 사람이
검토하는 기존 흐름을 대체하지 않고 그 위에 지속 가능한 실행 구조를
제공합니다.

```text
큰 목표
  │
  ▼
items.tsv ──▶ _batches/manifest.tsv ──▶ shard prompt
                                            │
                                            ▼
                                      agent runner 로그
                                            │
                                            ▼
                                  산출물 + QC + 재개 지점
```

## 왜 필요한가요?

긴 에이전트 작업은 대체로 비슷한 이유로 실패합니다.

- 작업이 하나의 context window보다 큽니다.
- 상당한 진척이 있었지만 전체 완료 전에 실행이 끝납니다.
- 병렬 worker가 같은 파일을 수정해 충돌합니다.
- 다음 실행이 완료, 부분 완료, 실패, 오래된 결과를 구분하지 못합니다.
- 로그는 있지만 기계가 읽을 수 있는 상태표가 없습니다.
- 검증 전에 worker가 상위 상태 파일을 완료로 바꿉니다.

Agent Batch Harness는 이를 단순한 운영 규칙으로 바꿉니다.

1. 실제 작업을 독립적인 item과 shard로 나눕니다.
2. 각 shard에 정확한 prompt를 생성합니다.
3. 순차 또는 제한된 병렬 방식으로 실행합니다.
4. prompt와 실행 로그를 함께 보존합니다.
5. 예상 산출물과 QC를 로컬에서 검증합니다.
6. 전체 대화를 다시 읽지 않고 manifest에서 재개합니다.

핵심 형식은 의도적으로 평범합니다. TSV, Markdown, JSON, 일반 텍스트 로그와
명시적인 상태 전이만 사용하므로 사람이 직접 읽고 복구할 수 있습니다.

## 무엇을 제공하나요?

Agent Batch Harness는 다음을 결합합니다.

- Python CLI
- 프로젝트 디렉터리 규칙
- shard prompt 생성기
- 외부 agent CLI 실행 wrapper
- 예상 파일과 QC JSON 검증
- 장기 작업을 위한 재개·인수인계 패턴

다음 역할까지 맡지는 않습니다.

- 모델이나 에이전트 서비스 제공
- 자율적인 프로젝트 기획
- 중앙 queue 또는 분산 scheduler
- 테스트, 코드 리뷰, 보안 경계 대체
- 특정 에이전트 제품에 대한 영구 종속

기본 `codex` runner는 다음 형태로 실행됩니다.

```bash
codex exec --cd <workdir> --skip-git-repo-check - < <prompt>
```

`dry-run` runner는 계획과 테스트에 사용합니다. 범용 `shell` runner는 생성된
prompt를 표준 입력으로 전달하므로 별도 adapter 없이 기존 CLI를 연결할 수
있습니다.

## 현재 기능

현재 pre-release는 **0.1.0a2**입니다.

| 명령 | 역할 |
|---|---|
| `plan` | item 목록을 shard로 나누고 manifest 생성 |
| `build-prompts` | shard별 Markdown prompt 생성 |
| `resume` | 다음 `pending` 또는 `failed` shard 표시 |
| `run` | `dry-run`, `codex`, `shell` runner로 선택된 shard 실행 |
| `verify` | 예상 산출물, QC JSON, 금지 문자열 검증 |
| `mark` | 사람이 shard 상태를 명시적으로 변경 |

`run`은 제한된 병렬 실행, timeout, 실패 후 계속 실행, 실행 후 verifier hook을
지원합니다. 초기 버전이므로 API와 manifest 형식은 정식 안정화 전까지 변경될
수 있습니다.

## 설치

Python 3.11 이상이 필요합니다. 저장소에서 설치할 때는 가상환경 사용을
권장합니다.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
agent-batch --help
```

Windows PowerShell에서는 다음처럼 활성화합니다.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
agent-batch --help
```

빌드된 wheel이 있다면 checkout 없이 설치할 수 있습니다.

```bash
python -m pip install path/to/agent_batch_harness-0.1.0a2-py3-none-any.whl
```

설치하지 않고 확인하려면 저장소 루트에서 실행합니다.

```bash
PYTHONPATH=src python3 -m agent_batch_harness --help
```

Agent Batch Harness 자체에는 Python 표준 라이브러리 이외의 runtime 의존성이 없습니다.

| 환경 | 설치 방식 | 현재 검증 수준 |
|---|---|---|
| Linux, Python 3.11-3.13 | editable install 또는 wheel | 단위·패키지·프로세스 테스트 완료 |
| macOS, Python 3.12 | editable install 또는 wheel | CI matrix 구성 |
| Windows, Python 3.12 | editable install 또는 wheel | CI matrix 구성 |
| Container와 CI worker | 동일한 pure Python wheel | 외부 runner 이미지에 따라 달라짐 |

manifest 잠금은 POSIX에서 `flock`, Windows에서 `msvcrt` byte-range lock을
사용합니다. shell과 process timeout 동작 차이는
[플랫폼 문서](docs/platforms.md)를 참고하세요.

> Agent Batch Harness가 실행하는 agent CLI는 외부 의존성입니다. 폐쇄망에서는 wheel과
> 선택한 agent runner를 모두 미리 반입해야 합니다.

## 5분 빠른 시작

저장소에 포함된 작은 예제를 사용합니다.

```bash
cd examples/tiny-edit

PYTHONPATH=../../src python3 -m agent_batch_harness plan \
  --items items.tsv \
  --batch-dir _batches \
  --batch-size 2

PYTHONPATH=../../src python3 -m agent_batch_harness build-prompts \
  --items items.tsv \
  --manifest _batches/manifest.tsv \
  --template prompt-template.md \
  --workdir .

PYTHONPATH=../../src python3 -m agent_batch_harness resume \
  --manifest _batches/manifest.tsv
```

예상 출력은 다음과 같습니다.

```text
shard_001    pending    _batches/shard_001.prompt.md    _batches/run-logs/shard_001.log
```

실제 에이전트를 호출하지 않고 실행 경로를 점검합니다.

```bash
PYTHONPATH=../../src python3 -m agent_batch_harness run \
  --manifest _batches/manifest.tsv \
  --runner dry-run \
  --workdir . \
  --limit 1
```

산출물을 검증합니다.

```bash
PYTHONPATH=../../src python3 -m agent_batch_harness verify \
  --items items.tsv \
  --workdir .
```

## 실제 runner 연결

Codex로 한 shard를 실행합니다.

```bash
agent-batch run \
  --manifest _batches/manifest.tsv \
  --runner codex \
  --workdir . \
  --limit 1
```

다른 CLI는 `shell` runner로 연결할 수 있습니다. 생성된 prompt는 표준 입력으로
전달되며 다음 환경변수도 함께 제공됩니다.

- `AGENT_BATCH_SHARD_ID`
- `AGENT_BATCH_PROMPT`
- `AGENT_BATCH_WORKDIR`
- `AGENT_BATCH_LOG`

```bash
agent-batch run \
  --manifest _batches/manifest.tsv \
  --runner shell \
  --shell-command 'your-agent-cli run --stdin' \
  --workdir . \
  --limit 1
```

runner와 verifier에 timeout을 적용할 수 있습니다. 제한 시간을 넘기면 종료 코드
`124`로 끝나고 해당 shard는 `failed`가 됩니다.

```bash
agent-batch run \
  --manifest _batches/manifest.tsv \
  --runner codex \
  --timeout 900
```

성공한 runner 뒤에 검증 명령을 실행하려면 다음과 같이 지정합니다.

```bash
agent-batch run \
  --manifest _batches/manifest.tsv \
  --runner shell \
  --shell-command 'your-agent-cli run --stdin' \
  --verify-command 'python3 -m agent_batch_harness verify --items items.tsv --manifest _batches/manifest.tsv --shard "$AGENT_BATCH_SHARD_ID" --workdir .' \
  --workdir . \
  --jobs 3
```

verifier가 0이 아닌 종료 코드를 반환하면 shard는 `failed`로 표시되고 출력은
같은 shard 로그에 추가됩니다.

## `items.tsv` 계약

`items.tsv`는 실제 작업 단위의 source of truth입니다. 필수 header와 하나 이상의
item 행이 있어야 합니다.

```text
item_id    source    output    qc    notes
```

```tsv
item_id	source	output	qc	notes
alpha	inputs/alpha.txt	outputs/alpha.md	qc/alpha.json	명확한 두 문장으로 다시 작성합니다.
beta	inputs/beta.txt	outputs/beta.md	qc/beta.json	명확한 두 문장으로 다시 작성합니다.
```

| 필드 | 의미 |
|---|---|
| `item_id` | manifest와 prompt에서 사용하는 안정적인 식별자 |
| `source` | worker가 읽을 입력 경로 |
| `output` | worker가 작성할 산출물 경로 |
| `qc` | 구조화된 검증·상태 JSON 경로 |
| `notes` | item별 지시사항과 추가 맥락 |

`item_id`는 가능한 한 유지하세요. 작업 내용이 본질적으로 바뀌었다면 새 item을
추가하거나 manifest를 의도적으로 다시 만드는 편이 안전합니다.

## Manifest와 상태

`agent-batch plan`은 `_batches/manifest.tsv`를 만듭니다.

```tsv
shard_id	prompt_path	item_count	first_item	last_item	status	log_path	started_at	attempt
shard_001	_batches/shard_001.prompt.md	2	alpha	beta	pending	_batches/run-logs/shard_001.log		0
shard_002	_batches/shard_002.prompt.md	1	gamma	gamma	pending	_batches/run-logs/shard_002.log		0
```

| 상태 | 의미 |
|---|---|
| `pending` | 실행 대기 |
| `running` | 현재 실행 중 |
| `succeeded` | verifier 없이 runner가 정상 종료 |
| `verified` | runner와 설정된 verifier가 모두 성공 |
| `failed` | runner 또는 검증 실패 |
| `skipped` | 의도적으로 실행하지 않음 |

manifest는 데이터베이스가 아니라 사람이 읽고 수정할 수 있는 운영 기록입니다.
여러 CLI process가 같은 manifest를 사용할 때 shard claim과 상태 쓰기는
advisory lock으로 보호됩니다.

claim할 때마다 `started_at`에 UTC 시각이 기록되고 `attempt`가 증가합니다. 중단된
process가 남긴 오래된 `running` 상태는 충분한 안전 시간을 지정해 회수합니다.

```bash
agent-batch reclaim --manifest _batches/manifest.tsv --older-than 3600
```

## Prompt template

template은 Python `string.Template`로 렌더링되는 일반 Markdown입니다.

- `$shard_id`
- `$item_count`
- `$first_item`
- `$last_item`
- `$items`

```md
# $shard_id 작업

아래 item만 완료합니다. 상위 집계 파일은 수정하지 않습니다.

## Items

$items
```

## 권장 운영 흐름

1. `items.tsv`를 작성합니다.
2. `prompt-template.md`를 작성합니다.
3. `agent-batch plan`으로 manifest를 만듭니다.
4. `agent-batch build-prompts`로 prompt를 생성합니다.
5. `agent-batch resume`으로 다음 shard를 확인합니다.
6. shard를 하나 또는 제한된 수만큼 실행합니다.
7. 산출물과 QC를 검증합니다.
8. 실패 원인을 수정하고 해당 shard만 다시 실행합니다.
9. 검증 후 parent memory와 handoff를 갱신합니다.

장기 프로젝트의 상위 상태는 다음처럼 별도 파일에 둘 수 있습니다.

```text
PROJECT_MEMORY.md
HANDOFF.md
STATUS.json
decision-ledger.tsv
qc/report.md
```

일반적으로 shard worker는 이 파일들을 수정하지 않고 parent orchestrator가
검증 후 갱신해야 합니다.

## Parent, worker, reviewer의 책임

**Parent orchestrator**

- manifest를 소유하고 다음 shard를 선택합니다.
- runner를 시작하거나 감독합니다.
- 결과를 검증하고 집계 상태를 갱신합니다.
- 다음 실행을 위한 handoff를 작성합니다.

**Shard worker**

- 지정된 source와 context만 읽습니다.
- 지정된 output과 QC 파일만 씁니다.
- 별도 지시가 없으면 상위 상태 파일을 수정하지 않습니다.
- 변경 파일과 검증 결과를 보고하고 shard 종료 후 멈춥니다.

**Reviewer**

- 예상 파일 존재와 QC JSON의 `pass` 판정을 확인합니다.
- TODO, placeholder, 작업 잔여물을 검색합니다.
- 변경 범위가 shard 경계를 벗어나지 않았는지 확인합니다.
- manifest 상태를 바꿔도 되는지 판단합니다.

## 검증

기본 검증은 다음을 확인합니다.

- 모든 `output` 파일이 존재하는지
- 모든 `output`이 비어 있지 않은 UTF-8 text인지
- 모든 `qc` 파일이 존재하는지
- QC 파일이 JSON object이고 `"pass": true`를 포함하는지
- output에 `TODO`, `TBD`, `placeholder`, `FIXME`가 남아 있지 않은지

```bash
agent-batch verify --items items.tsv --workdir .
```

추가 금지 문자열을 지정할 수 있습니다.

```bash
agent-batch verify \
  --items items.tsv \
  --workdir . \
  --forbid 'DO NOT COMMIT' \
  --forbid 'SOURCE_TEXT_LEFT_HERE'
```

QC JSON을 사용하지 않는 흐름은 `--no-json`을 사용합니다.

```bash
agent-batch verify --items items.tsv --workdir . --no-json
```

특정 shard만 검증할 수도 있습니다.

```bash
agent-batch verify \
  --items items.tsv \
  --manifest _batches/manifest.tsv \
  --shard shard_002 \
  --workdir .
```

## 재개와 복구

다음 실행 대상을 찾습니다.

```bash
agent-batch resume --manifest _batches/manifest.tsv
```

상태를 수동으로 정정합니다.

```bash
agent-batch mark \
  --manifest _batches/manifest.tsv \
  --shard shard_003 \
  --status failed
```

복구 원칙은 단순합니다.

- runner가 실패하면 로그를 보존하고 shard를 `failed`로 둡니다.
- 파일 작성 전에 멈췄다면 로그를 확인한 뒤 같은 shard를 다시 실행합니다.
- shard가 너무 크다면 item 범위를 더 작게 나누고 manifest를 다시 만듭니다.
- 산출물이 검증에 실패하면 수정될 때까지 완료로 표시하지 않습니다.
- 산출물은 유효하지만 상태만 오래됐다면 `mark`로 명시적으로 정정합니다.

## 안전한 병렬 실행

병렬 실행은 다음 조건을 모두 만족할 때 적합합니다.

- shard별 output 경로가 겹치지 않습니다.
- worker가 공용 집계 파일을 수정하지 않습니다.
- 각 shard 종료 후 검증합니다.
- manifest 상태 변경이 lock으로 보호됩니다.
- 외부 서비스의 rate limit과 동시 실행 제한을 알고 있습니다.

```bash
agent-batch run \
  --manifest _batches/manifest.tsv \
  --runner codex \
  --workdir . \
  --jobs 3
```

기본 `--jobs 1`은 첫 실패에서 멈춥니다. 이후 shard도 계속 실행하려면
`--continue-on-failure`를 추가합니다. 병렬 mode에서는 이미 시작된 sibling을 한
실패가 취소하지 않습니다.

> Manifest lock은 상태 파일을 보호할 뿐 output 파일 충돌을 막지 않습니다.
> 서로 겹치지 않는 output 경로는 반드시 사용자가 보장해야 합니다.

## Skills와 agents

저장소에는 재사용 가능한 역할 정의가 포함됩니다.

- `skills/generic-shard/SKILL.md`
- `agents/parent-orchestrator.md`
- `agents/shard-worker.md`
- `agents/reviewer.md`

모두 일반 Markdown이므로 프로젝트에 복사하거나 Codex Skill, plugin, 다른 agent
runtime의 prompt 일부로 사용할 수 있습니다.

## 저장소 구조

```text
src/agent_batch_harness/             CLI와 핵심 실행 로직
agents/                    parent, worker, reviewer 역할
skills/generic-shard/      재사용 가능한 shard skill
examples/tiny-edit/        실행 가능한 작은 예제
docs/                      설계, workflow, 플랫폼, recipe 문서
tests/                     계약과 회귀 테스트
tools/                     release, artifact, SBOM 검사
```

## 개발과 검증

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m agent_batch_harness --help
python3 tools/release_check.py
```

예제 산출물도 직접 검증할 수 있습니다.

```bash
cd examples/tiny-edit
PYTHONPATH=../../src python3 -m agent_batch_harness verify --items items.tsv --workdir .
```

민감한 작업에서 shell runner를 사용하거나 공개 release를 준비하기 전에는
[보안 정책](SECURITY.md), [공개 정책](PUBLICATION_POLICY.md),
[release 절차](docs/release.md)를 확인하세요.

추가 문서:

- [설계](docs/design.md)
- [Workflow](docs/workflow.md)
- [플랫폼 지원](docs/platforms.md)
- [실전 recipe](docs/recipes.md)
- [오픈소스 준비 상태](docs/readiness.md)
- [보안 감사 기록](docs/security-audit.md)

## 라이선스

MIT License. 자세한 내용은 [LICENSE](LICENSE)를 참고하세요.
