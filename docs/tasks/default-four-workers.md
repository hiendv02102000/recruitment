# Task: Default to four workers

- Status: `AWAITING_HUMAN_TEST`
- Implementer: Codex
- Human tester: Not yet assigned
- Scope / challenge: `fv-sec-001-software-engineer-challenge`
- If blocked: None

## 1. Brainstorm

- [x] Brainstorm complete

**Original request:** Set the default worker count to four.

**Problem and goal:** The default follows the CPU count, which can create more
processes than desired. Use four by default while preserving explicit overrides.

**In scope:** Worker selection, tests, documentation, and a full-data timing comparison.

**Out of scope:** CSV parsing, aggregation, report formats, and CLI options.

**Assumptions / risks:** Four is a fixed default even on machines with fewer
CPUs. Performance depends on the host and workload.

**Approach and rationale:** Use a named constant; retain the existing threshold,
fallback behavior, and optional API argument.

| ID | Acceptance criterion | Verification method |
| --- | --- | --- |
| AC-01 | Large inputs use four workers by default. | Unit test and full-data run |
| AC-02 | Explicit worker counts and the sequential threshold still work. | Unit tests and review |
| AC-03 | Correct results and thread-safe aggregation remain intact. | Existing tests and compare full-data reports |
| AC-04 | Document the default and report observed performance. | Documentation review and timing |

## 2. Plan

- [x] Plan complete

| Order | Work item | File / component | Dependencies |
| --- | --- | --- | --- |
| 1 | Set default and test overrides | Aggregator and tests | None |
| 2 | Review diff and run tests | Challenge | 1 |
| 3 | Compare full-data results and timings | Challenge dataset | 1 |
| 4 | Document results and hand over human scenarios | Solution and task record | 2, 3 |

**Verification plan:** Run the unit suite; time four and twelve processes on
the same full dataset and verify report hashes.

**Environment / data:** Local Windows Python and extracted `ad_data.csv`.

**Recovery if needed:** Restore the changed default if a correctness issue arises.

## 3. Implement

- [x] Implementation complete

**Changes made:** Set a four-worker default, retain explicit worker overrides,
add selection tests, and document the observed performance tradeoff.

**Deviations from the plan:** None.

## 4. Code review

- [x] Code review complete; no required fixes remain

**Reviewer / tool:** Codex self-review.

**Reviewed scope:** Working-tree changes to worker selection, tests, and
solution documentation. No required findings; the threshold, fallback,
per-process aggregation, and explicit override remain unchanged.

## 5. Test

- [x] Required checks passed

| Criterion / test case | Command or check | Directory / data / environment | Result | Evidence / reason |
| --- | --- | --- | --- | --- |
| AC-01, AC-02, AC-03 | `python -m unittest discover -s tests` | Challenge directory; Windows Python 3.15.2 | PASS | 40 tests passed, including default and explicit worker selection and parallel correctness. |
| AC-03, AC-04 | Full-data runs with `aggregate(path, workers=N)` and `write_reports` | Windows, 12 available logical CPUs, 1,043,304,870-byte input | PASS | All runs read 26,843,544 rows and 50 campaigns. Both report SHA-256 hashes matched the existing expected results after line-ending normalization. |

**Timing evidence:** Alternating runs in order 12, 4, 4, 12 workers took
16.848, 25.552, 24.538, and 17.294 seconds respectively, including report
writing. Means: 17.071 seconds for 12 and 25.045 seconds for 4. This host's
four-worker default is about 47% slower. Worker-process memory was not measured.

**Remaining issues:** Human acceptance remains pending.

## 6. Human test

- [x] Instructions delivered; status is `AWAITING_HUMAN_TEST`
- [ ] User confirmed that all acceptance criteria passed

**Version tested:** Working-tree diff setting the default to four workers.

**Setup:** From the challenge directory, use Python 3.10 or newer.

| ID / criterion | Actions | Expected result | Actual result | PASS / FAIL / PENDING |
| --- | --- | --- | --- | --- |
| HT-01 / AC-01, AC-03 | Run `python aggregator.py --input ad_data.csv --output results` with the full dataset. | Completes with 26,843,544 records and the expected CTR and CPA reports. | Not yet received | PENDING |
| HT-02 / AC-02 | Run the automated test suite with `python -m unittest discover -s tests`. | All tests pass, including the default and explicit worker cases. | Not yet received | PENDING |

**Feedback / reproduction steps:** Not yet received.

**User confirmation:** Not yet confirmed.

## Completion

- [ ] The steps above meet their exit criteria; no required fixes remain
- [ ] User confirmation of human test is recorded
- [ ] Status is `DONE`

**Handoff result:** Automated checks pass; the default is four, with a measured
latency tradeoff on the local machine. Human acceptance is pending.
