# Task: CSV advertising performance aggregator

> The single-pass implementation is current again: on 2026-10-31 the user
> requested restoring it after comparing the two benchmark results. The
> [hash-partitioning record](hash-partitioned-aggregator.md) is historical.
> The 104.581-second / 24.30 MiB measurement below is the original measured run
> for this restored version, not a fresh benchmark after restoration.

- Status: `AWAITING_HUMAN_TEST`
- Implementer: Codex
- Human tester: User, confirmation pending
- Scope / challenge: `fv-sec-001-software-engineer-challenge/`
- If blocked: None

## Restoration on 2026-10-31

**Request and approach (Brainstorm):** The user requested reverting the
171.954-second / 30.13 MiB hash-partitioned implementation to the original
104.581-second / 24.30 MiB single-pass implementation. Restore the exact earlier
source, original 30-test suite, usage guide, and challenge README. Keep existing
staged changes and report files. Retain partition benchmark artifacts only as
historical evidence; they are not used by the restored CLI.

**Plan:** Restore only the four inspected files from their original versions
already staged in Git; inspect the restored source, verify exact content against
that baseline, run its 30 tests, check known report values and documentation
links, then return to human acceptance. No requirement to approve the approach
or performance target remains unresolved.

**Implementation:** Executed
`git restore --worktree -- fv-sec-001-software-engineer-challenge/aggregator.py fv-sec-001-software-engineer-challenge/tests/test_aggregator.py fv-sec-001-software-engineer-challenge/SOLUTION.md fv-sec-001-software-engineer-challenge/README.md`.
This changes the working copy only; the index and report files are preserved.
The CLI again calls `aggregate()` directly; partitioning, worker threads, and
partition-only command-line options are removed. Reporting and validation are
the original single-pass implementation.

**Code review:** Codex read the original staged source and the partitioning diff
before restoration. After restoration,
`git diff --exit-code -- fv-sec-001-software-engineer-challenge/aggregator.py fv-sec-001-software-engineer-challenge/tests/test_aggregator.py fv-sec-001-software-engineer-challenge/SOLUTION.md fv-sec-001-software-engineer-challenge/README.md`
returned 0: these four files exactly match their earlier staged versions. No
required findings. Original acceptance criteria and human scenarios below apply
again. Full-dataset benchmark evidence is reused only because the restored code
is identical, with newline normalization accounted for in its fingerprint.

| Verification after restoration | Result | Evidence |
| --- | --- | --- |
| Exact original source/tests/usage content | PASS | Four-file Git diff returned 0 |
| `python -m unittest discover -s tests -v` | PASS | Executed from the challenge directory after restoration: 30 tests passed in 1.470 seconds |
| Source fingerprint, report contents, and documentation links | PASS | Python here-string compared all four restored files with `git show :<path>`; normalized source SHA-256 matches `02b8b1b1ce681bdfb04d7eebdd307ddf44dab3e9da2cb36fbdcd5de9edb9ad3c`; both existing full-data report fingerprints match; 11 relative documentation links resolve |
| Pre-commit validation on 2026-10-31 | PASS | 30 tests passed in 1.430 seconds; 46 relative links resolve across workflow/skill/solution documentation; single-pass source and tests still match the original staged versions |
| Fresh full-dataset benchmark | NOT_RUN | Not repeated: exact original implementation restored; original measured results remain labeled with their original date |

**Human handoff:** Restoration checks passed. The original HT-01–04 in section
6 apply to the restored version; user acceptance remains unconfirmed, so the
workflow status is `AWAITING_HUMAN_TEST`. The benchmark figures above remain
historical measurements rather than a new runtime claim.

**Commit request (2026-10-31):** The user explicitly requested committing the
restored solution, workflow documentation, historical benchmark evidence, and
prompt log. This authorizes the commit without implying human acceptance; the
workflow status remains `AWAITING_HUMAN_TEST`. A pre-commit whitespace warning
in `PROMPTS.md` is an intentional trailing space from a verbatim user prompt;
preserving the original prompt takes precedence over trimming that space.

## 1. Brainstorm

- [x] Brainstorm complete

**Original request:** Run `project-workflow`; clarification: "Implement the CSV aggregator challenge". See root `PROMPTS.md`.

**Problem and goal:** Produce the challenge's two ranked campaign reports from
the supplied large CSV without loading all records into memory.

**In scope:** A Python CLI, streaming aggregation, input validation, deterministic
ranking, CSV reports, correctness tests, usage documentation, and a measured run
on the provided dataset. Preserve the existing `count_campaigns.py` and workflow
documentation changes.

**Out of scope:** Docker, database services, parallel processing, commits, pushes,
or submission by email.

**Assumptions / questions / risks:** Python 3.10+ and its standard library are
sufficient (installed interpreter: Python 3.15.2). The input is UTF-8 with an
optional BOM. Require exactly the six documented columns, in any order, with
unique names. Skip empty records; require nonempty campaign IDs, calendar dates
in YYYY-MM-DD form, nonnegative ASCII integer counts, and finite nonnegative
decimal spend. Header-only input produces header-only reports; an empty file is
an error. Define CTR as zero when impressions are zero, CPA as blank when
conversions are zero, and exclude those campaigns from CPA ranking. Format CTR
to four decimals and CPA to two using half-up rounding; preserve total spend's
decimal precision with at least two decimal places. Sort before rounding and
break ties by campaign ID ascending. Existing output names are replaced on
success, each via an atomic file replacement. Memory grows with distinct
campaigns, rather than input rows; arbitrary campaign cardinality can still
require substantial memory.

**Approach and rationale:** Use `csv.reader` and per-campaign totals, with Decimal
for spend and exact rational comparisons for the small final rankings. This
avoids an external dataframe dependency and whole-file memory costs. Validate
all input before writing reports; stage both files before replacing outputs.
Reject input/output path collisions. A disk-backed database is unnecessary for
the supplied campaign cardinality and would add operational complexity.

| ID | Acceptance criterion | Verification method |
| --- | --- | --- |
| AC-01 | CLI accepts `--input` and `--output`, sums all four metrics by campaign, and writes the seven required columns to `top10_ctr.csv` and `top10_cpa.csv`. | Manual-value fixture, CLI integration tests, human test |
| AC-02 | CTR ranks descending, CPA ascending; lists contain at most 10 campaigns; ties use ID ascending and ranking uses unrounded exact ratios. | Boundary, tie, and close-ratio tests; code review |
| AC-03 | Zero denominators, no eligible CPA campaigns, header-only input, and fewer than 10 campaigns follow the policies above. | Unit and CLI tests; human test |
| AC-04 | Missing/unreadable files, invalid schema or records, bad encoding, and output failures exit nonzero with a clear message and no traceback. Invalid input leaves existing reports unchanged. | Negative integration tests and review |
| AC-05 | Spend accumulation is exact for decimal inputs; reporting uses documented rounding and correctly quotes CSV IDs. | Decimal, rounding, and CSV round-trip tests |
| AC-06 | The provided 1,043,304,870-byte dataset completes using one streaming pass and O(distinct campaigns) aggregation memory; actual time and memory measurements are recorded. | Code review and measured full-data execution |
| AC-07 | Setup, dependencies, policies, test commands, benchmark evidence, and human acceptance scenarios are documented without changing the original challenge requirements. | Documentation/link review and human test |

## 2. Plan

- [x] Plan complete

| Order | Work item | File / component | Dependencies |
| --- | --- | --- | --- |
| 1 | Implement streaming parsing, validation, exact totals, ranking, output staging, and CLI | `aggregator.py` | None |
| 2 | Add the challenge example as a reproducible fixture and behavior tests | `tests/`, `tests/fixtures/example.csv` | 1 |
| 3 | Document setup, run commands, policies, and test procedure; link the solution from the challenge README and add a reproducible benchmark helper | `SOLUTION.md`, `README.md`, `benchmark.py` | 1–2 |
| 4 | Review every new file and the relevant diff against AC-01–07; fix required findings and review again | This record and implementation | 1–3 |
| 5 | Run tests, CLI smoke checks, full-data benchmark, inspect the generated outputs, and record actual evidence | `results/`, benchmark log, this record, `SOLUTION.md` | 4 |
| 6 | Deliver acceptance actions and leave status awaiting the user's report | This record and conversation | 5 |

**Verification plan:** From the challenge directory run
`python -m unittest discover -s tests -v`; run the CLI on
`tests/fixtures/example.csv` and compare all values to the manually calculated
results in section 6. Exercise invalid schema, invalid metrics/dates, malformed
CSV, empty and missing files, output collisions, and retained existing outputs
on errors. Run the supplied full dataset, measure wall time and peak process
working set, and record the exact command and environment. Review whitespace
with `git diff --check` and validate relative Markdown links in new documents.

**Environment / data:** Windows PowerShell; Python 3.15.2; standard library only.
The extracted dataset is already present and ignored by Git. For a fresh checkout,
download the actual archive data using Git LFS if needed and extract with
`python -m zipfile -e ad_data.csv.zip .` from the challenge directory.

**Recovery if needed:** Input is read-only. Use a separate `--output` directory
to preserve earlier reports, or rerun to regenerate them. Temporary output files
are cleaned on handled failures. Each report is replaced atomically; the two
replacements are not a transaction if an OS error occurs between them.

## 3. Implement

- [x] Implementation complete

**Changes made:** Added `aggregator.py`, the challenge's example fixture,
30 behavior tests, a no-dependency Windows timing/memory benchmark wrapper,
and `SOLUTION.md`. Added an implementation section to the challenge README
while retaining its original requirements. Ignore only manual acceptance output
directories under `results/manual-*/`; full-dataset reports remain trackable.
Implementation was read in a separate review pass; measured results will be
added after testing.

**Deviations from the plan:** None.

## 4. Code review

- [x] Code review complete; no required fixes remain

**Reviewer / tool:** Codex, separate self-review pass.

**Reviewed scope:** Read the tracked challenge README and ignore-rule diff,
all of `aggregator.py`, `benchmark.py`, the fixture, all 30 tests, `SOLUTION.md`,
and this task's acceptance criteria. Preserved the initial root README,
workflow/skill files, and existing counting utility. Confirmed streaming
aggregation, exact arithmetic and ranking, all denominator policies, complete
validation before output, input alias protection, and staged-file cleanup.

**Findings:** No required code findings. The two output replacements are not a
transaction; this limitation and recovery are explicitly documented. Reviewed
the final benchmark log, report contents, README additions, and measured values
in `SOLUTION.md` against actual command output. No required findings remain.
Human acceptance remains pending regardless of automated results.

**Fix loop:** The first suite run passed 29 tests and failed the quoted-ID test:
the fixture helper used Windows newline translation, so it wrote CRLF inside
an ID expected to contain LF. Returned to Implement to set `newline=""` when
writing test fixtures and cover both embedded LF and CRLF. Reviewed that test
diff: it now preserves the intended input bytes and checks both cases. The
production CSV reader/writer already preserves these newlines; no production
change was needed. Returned to Test for the full suite.

## 5. Test

- [x] Required checks passed

| Criterion / test case | Command or check | Directory / data / environment | Result | Evidence / reason |
| --- | --- | --- | --- | --- |
| Initial test run | `python -m unittest discover -s tests -v` | Challenge directory, Windows | FAIL | 30 tests, 29 passed, 1 fixture newline failure; fix and follow-up review recorded above |
| AC-01–05 | `python -m unittest discover -s tests -v` | Challenge directory, Python 3.15.2 | PASS | 30 tests passed in 1.249 seconds after the fixture correction |
| Benchmark instrumentation | `python -c "from benchmark import peak_working_set_bytes; peak = peak_working_set_bytes(); assert peak is not None and peak > 0; print(f'Windows peak-memory API check: {peak:,} bytes')"` | Challenge directory, Windows | PASS | Windows API returned 20,389,888 bytes for the instrumentation smoke check |
| AC-06 | `python benchmark.py --input ad_data.csv --output results` (captured with `Tee-Object -FilePath benchmark-full.txt`) | Challenge directory; 1,043,304,870-byte CSV; Windows 11 / Python 3.15.2 64-bit / Intel Core i7-10750H | PASS | 26,843,544 records, 50 campaigns, 104.581 seconds, peak working set 25,477,120 bytes / 24.30 MiB; exit 0 |
| AC-01,02,05,06 | Independent integer-cents reference, command below | Challenge directory; entire supplied dataset; no production code imported | PASS | Independently summed 26,843,544 records / 50 campaigns; all 10 rows in each report match every value and campaign order. Reference script elapsed time: 3363.931 seconds (separate from the production benchmark). |
| AC-07 | `git diff --check`; Python relative-link and whitespace checks | Repository root, final changed/new documentation | PASS | No tracked whitespace errors; relative links resolve and new implementation files have no trailing whitespace |
| Application build / external services | N/A | Standard-library Python CLI | N/A | No compiled build, database, frontend, or third-party dependency installation is needed |

**Remaining issues:** No automated-check failures remain. Only human acceptance
is pending. Python 3.10+ compatibility was reviewed, but runtime tests were
executed only with the installed Python 3.15.2 on Windows, not other interpreters
or operating systems.

**Independent full-data verification command:** The following PowerShell
here-string was piped to Python from the challenge directory. It is specific to
the supplied dataset (all spend values have at most two decimal places and every
campaign has positive impressions and conversions). It independently sums
integer cents, calculates ratios with Decimal, sorts all 50 campaign IDs, and
compares all output columns, rather than calling production helpers.

```powershell
@'
import csv
from decimal import Decimal, getcontext, ROUND_HALF_UP
from pathlib import Path
from time import perf_counter

start = perf_counter()
getcontext().rounding = ROUND_HALF_UP
totals = {}
count = 0
with Path('ad_data.csv').open(encoding='utf-8', newline='') as source:
    reader = csv.reader(source)
    assert next(reader) == ['campaign_id', 'date', 'impressions', 'clicks', 'spend', 'conversions']
    for campaign, day, impressions, clicks, spend, conversions in reader:
        whole, _, fractional = spend.partition('.')
        assert whole.isdigit() and (not fractional or fractional.isdigit()) and len(fractional) <= 2
        cents = int(whole) * 100 + int(fractional.ljust(2, '0'))
        current = totals.setdefault(campaign, [0, 0, 0, 0])
        for index, value in enumerate([int(impressions), int(clicks), cents, int(conversions)]):
            current[index] += value
        count += 1
assert count == 26843544 and len(totals) == 50
by_ctr = sorted(totals, key=lambda key: (-Decimal(totals[key][1]) / totals[key][0], key))[:10]
by_cpa = sorted(totals, key=lambda key: (Decimal(totals[key][2]) / totals[key][3], key))[:10]
for filename, ranking in [('top10_ctr.csv', by_ctr), ('top10_cpa.csv', by_cpa)]:
    with (Path('results') / filename).open(encoding='utf-8', newline='') as source:
        rows = list(csv.reader(source))
    assert rows[0] == ['campaign_id', 'total_impressions', 'total_clicks', 'total_spend', 'total_conversions', 'CTR', 'CPA']
    expected = []
    for campaign in ranking:
        impressions, clicks, cents, conversions = totals[campaign]
        expected.append([campaign, str(impressions), str(clicks), f'{Decimal(cents) / 100:.2f}', str(conversions), f'{Decimal(clicks) / impressions:.4f}', f'{Decimal(cents) / 100 / conversions:.2f}'])
    assert rows[1:] == expected, filename
    print(f'PASS: {filename}: all 10 rows, every value and exact campaign order match the independent reference.')
print(f'PASS: independently summed {count:,} records / {len(totals)} campaigns in {perf_counter() - start:.3f} seconds using integer cents; no production code imported.')
'@ | python -
```

## 6. Human test

- [x] Instructions delivered; status is `AWAITING_HUMAN_TEST`
- [ ] User confirmed that all acceptance criteria passed

**Version tested:** Uncommitted CSV aggregator implementation, 2026-10-30.
`aggregator.py` SHA-256:
`02B8B1B1CE681BDFB04D7EEBDD307DDF44DAB3E9DA2CB36FBDCD5DE9EDB9AD3C`.
All 30 tests pass; the full benchmark log and both generated result reports
are included. No commit or push was requested or performed.

**Setup:** From the repository root run
`cd fv-sec-001-software-engineer-challenge`. Use Python 3.10+.

| ID / criterion | Actions | Expected result | Actual result | PASS / FAIL / PENDING |
| --- | --- | --- | --- | --- |
| HT-01 / AC-01,02,05 | Run `python aggregator.py --input tests/fixtures/example.csv --output results/manual-example`; open both CSVs. | CTR IDs: CMP001, CMP002, CMP003. CPA IDs: CMP001, CMP003, CMP002. CMP001 totals: 26000 impressions, 640 clicks, 93.70 spend, 27 conversions, CTR 0.0246, CPA 3.47. All seven columns are present. | Not received | PENDING |
| HT-02 / AC-03,04 | Create a CSV with the example header and one row `ZERO,2025-01-01,0,0,0,0`; run it to a separate directory. Then replace its spend with `NaN` and rerun to the same directory. | First run: CTR row has CTR 0.0000 and blank CPA; CPA report has only its header. Second run: nonzero exit and a line-specific error; both previous reports remain unchanged. | Not received | PENDING |
| HT-03 / AC-04 | Run `python aggregator.py --input missing.csv --output results/manual-missing`. | Nonzero exit, readable error, no traceback and no reports created. | Not received | PENDING |
| HT-04 / AC-06,07 | Follow `SOLUTION.md` to run the actual supplied dataset to `results/manual-full`; inspect both outputs and compare campaign order and values with the provided `results/` files. | Successful completion, 10 rows per report, CTR descending, CPA ascending, and values matching the supplied results. Runtime is machine-dependent. | Not received | PENDING |

**Feedback / reproduction steps:** Not yet received.

**User confirmation:** Not yet confirmed.

## Completion

- [ ] The steps above meet their exit criteria; no required fixes remain
- [ ] User confirmation of human test is recorded
- [ ] Status is `DONE`

**Handoff result:** Streaming CLI, exact aggregation/ranking, validation,
30 passing tests, both full-data CSV reports, setup/decision documentation,
benchmark wrapper and measured log, and independent report verification are
ready. The supplied 1.04 GB file processed in 104.581 seconds with 24.30 MiB
peak working set. HT-01–04 await the user's PASS/FAIL report; status remains
`AWAITING_HUMAN_TEST` until the workflow's human completion criterion is met.
