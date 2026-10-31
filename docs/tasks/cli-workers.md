# Task: Configure workers from the command line

- Status: `AWAITING_HUMAN_TEST`
- Implementer: Codex
- Human tester: Not yet assigned
- Scope: `fv-sec-001-software-engineer-challenge`

## 1. Brainstorm

- [x] Brainstorm complete

**Goal:** Default to four workers and allow choosing the worker count at runtime.

**Approach:** Add `--workers N` to the existing CLI and pass its value to
`aggregate`. Require a positive integer; keep the existing sequential threshold
and parallel fallback. Existing Python callers continue to work unchanged.

| ID | Acceptance criterion | Verification method |
| --- | --- | --- |
| AC-01 | The CLI defaults to four and forwards a supplied worker count. | CLI forwarding test |
| AC-02 | One or more workers produce correct reports; small inputs remain sequential. | CLI and existing aggregation tests |
| AC-03 | Zero, negative, missing, and non-integer values fail clearly without output. | CLI error tests |
| AC-04 | Usage describes the option and threshold. | Documentation and help review |

## 2. Plan

- [x] Plan complete

1. Add and validate the CLI option, with `DEFAULT_WORKERS` as its default.
2. Add forwarding, valid-output, and invalid-input tests; update usage.
3. Review the diff and run the automated suite and help check.
4. Hand over the human scenarios below.

**Environment:** Local Python and the example CSV fixture.

**Recovery:** Revert this option if a correctness issue arises; no data migration.

## 3. Implement

- [x] Implementation complete

**Changes made:** Added and documented `--workers`, positive-integer
validation, and tests for forwarding, valid reports, and invalid options.

## 4. Code review

- [x] Code review complete; no required fixes remain

**Reviewer:** Codex self-review of the full aggregator, test, and solution
diff against the acceptance criteria. No required findings. The documented
existing fallback also applies if the Windows process-pool limit is exceeded.

## 5. Test

- [x] Required checks passed

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests` | PASS: 43 tests, including option forwarding, invalid arguments, output values, and existing parallel and thread-safety coverage. |
| `python aggregator.py --help` | PASS: shows `--workers` and default 4. |
| Full dataset via CLI `--workers 12` | PASS: 26,843,544 records, 50 campaigns, 16.72 seconds; both report SHA-256 hashes matched expected after line-ending normalization. Outputs were temporary. |
| `git diff --check` | PASS. |

Checks ran in the challenge directory on local Windows with Python 3.15.2,
except `git diff --check`, which ran at the repository root.

## 6. Human test

- [x] Instructions delivered; status is `AWAITING_HUMAN_TEST`
- [ ] User confirmed that all acceptance criteria passed

**Version tested:** Working-tree diff after implementation.

**Setup:** Run from the challenge directory with Python 3.10 or newer.

| ID | Actions | Expected result | Actual result | Status |
| --- | --- | --- | --- | --- |
| HT-01 / AC-01, AC-02 | Run `python aggregator.py --input tests/fixtures/example.csv --output results/manual-example --workers 12`. | Five records are processed and the expected CTR and CPA reports are produced. | Not yet received | PENDING |
| HT-02 / AC-03 | Repeat with `--workers 0`. | The CLI reports a positive integer is required and exits without processing. | Not yet received | PENDING |

**User confirmation:** Not yet received.

## Completion

- [ ] Human acceptance recorded and status `DONE`.
