# Task: Optimize CSV row processing

- Status: `AWAITING_HUMAN_TEST`
- Implementer: Codex
- Human tester: Not yet assigned
- Scope: CSV aggregator hot path

## 1. Brainstorm

- [x] Brainstorm complete

**Goal:** Find and retain a code optimization only if it improves latency
without changing correctness, validation, memory bounds, or thread safety.

**Approach:** Prototype and benchmark alternatives in temporary files against
the existing code, then keep promising candidates only if full-data comparisons
and the existing correctness checks pass. Fixed worker defaults remain intact.

| ID | Acceptance criterion | Verification |
| --- | --- | --- |
| AC-01 | Full-dataset performance improves in comparable alternating runs. | Timed runs on identical data and worker count |
| AC-02 | Reports, errors, exact arithmetic, and column reordering remain correct. | Full-data hashes and automated tests |
| AC-03 | Worker isolation and bounded streaming behavior remain unchanged. | Review and concurrency tests |
| AC-04 | Any adopted non-obvious optimization is documented. | Documentation review |

## 2. Plan

- [x] Plan complete

1. Prototype alternatives on a representative sample and compare exact totals.
2. Benchmark promising candidates on the full dataset; reject slower changes.
3. Add necessary regression tests and documentation for retained changes.
4. Review the complete diff, run automated tests, and hand over human scenarios.

**Environment:** Windows, Python 3.15.2, extracted 1 GB dataset.

**Recovery:** Do not adopt slower or incorrect candidates; temporary files are isolated.

## 3. Implement

- [x] Implementation complete

**Changes made:** Parse valid ASCII integer fields directly, retaining the
existing helper for invalid values. Added regression tests and documented the
optimization and measured performance. No changes to worker state or buffers.

## 4. Code review

- [x] Code review complete; no required fixes remain

**Reviewer:** Codex self-review of the source and tests against the criteria.
No required findings: valid values use the same predicates and `int` as the
helper, invalid values use the existing helper, and evaluation order is
unchanged. Worker isolation, range handling, and Decimal arithmetic are intact.

## 5. Test

- [x] Required checks passed

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests` | PASS: 44 tests on Windows / Python 3.15.2. Includes reordered columns, invalid counts and spend, error precedence, parallel fallback, exact ratios, and concurrent calls. |
| Full-data candidate comparison | PASS: isolated copies processed 26,843,544 rows / 50 campaigns each; both report hashes matched expected after CRLF normalization in every run. |
| `git diff --check` | PASS. |

**Timing evidence:** The paired full-data runs alternated isolated copies of
the CLI, with identical worker counts and temporary output directories. For
four workers, baseline ran in 27.46 and 30.82 seconds; candidate ran in 23.99
and 24.85 seconds (means 29.14 and 24.42). For twelve workers, the initial
baseline ran in 20.68 and 17.06 seconds; candidate ran in 23.29 and 16.91.
Because these times were noisy, a second alternating comparison produced
baseline 16.60, 17.01, 17.03 and candidate 16.26, 16.91, 16.40 seconds.
Across both comparisons, medians were 17.03 and 16.91 seconds. The differences
are host- and load-dependent. Combined worker memory was not measured.

**Sample experiments:** On 500,000 rows, the median of four sequential worker
measurements was 1.4699 seconds for baseline and 1.3919 for direct integer
parsing, with identical totals. An `itemgetter` field-selection prototype was
slower and was not adopted. No production data or source was changed by these
temporary experiments.

## 6. Human test

- [x] Instructions delivered; status is `AWAITING_HUMAN_TEST`
- [ ] User confirmed that all acceptance criteria passed

**Version tested:** Working-tree diff after implementation.

**Setup:** Run from the challenge directory with Python 3.10 or newer.

| ID | Actions | Expected result | Actual result | Status |
| --- | --- | --- | --- | --- |
| HT-01 / AC-01, AC-02 | Run `python aggregator.py --input ad_data.csv --output results --workers 12`. | Processes 26,843,544 rows and produces the expected CTR and CPA reports. | Not yet received | PENDING |
| HT-02 / AC-02, AC-03 | Run `python -m unittest discover -s tests`. | All tests pass. | Not yet received | PENDING |

**User confirmation:** Not yet received.

## Completion

- [ ] Human acceptance recorded and status `DONE`.
