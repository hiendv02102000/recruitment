# Task: Hash partitioning and thread-safe streaming aggregation

> Historical revision: on 2026-10-31 the user requested reverting this approach
> after comparing its measured overhead with the original implementation.
> The code and usage documentation have been restored to the single-pass
> version. The [current task record](csv-aggregator.md) tracks that restoration.
> Results, benchmark measurements, and the handoff status below describe this
> earlier revision; its human test scenarios are no longer the active handoff.

- Status: `AWAITING_HUMAN_TEST`
- Implementer: Codex
- Human tester: User, pending
- Scope / challenge: `fv-sec-001-software-engineer-challenge/`
- If blocked: None

## 1. Brainstorm

- [x] Brainstorm complete

**Original request:** " applying a Hash Partitioning + Streaming Aggregation solution. You must ensure thread safety." See root `PROMPTS.md` for the verbatim prompt.

**Problem and goal:** Replace the CLI's whole-campaign aggregation dictionary
with disk hash partitions and independently owned streaming worker dictionaries,
while preserving the challenge's exact output and error behavior.

**In scope:** Deterministic partitioning, configurable partition/worker counts,
isolated temporary workspaces, concurrent partition aggregation, bounded candidate
merging, serialization of report writes within a process, concurrency tests,
documentation, and a new full-data benchmark.

**Out of scope:** Recursive spill of oversized partitions, database services,
process pools, cross-process locks, commits, pushes, or submission.

**Assumptions / questions / risks:** Preserve all earlier numeric, schema,
rounding, and invalid-input policies. Default to 32 partitions and 4 worker
threads, with limits of 256 partitions and 32 workers to bound open files and
thread creation. Temporary storage must fit the partitioned CSV (including
original line numbers). Memory depends on active partition cardinality; skew
can place many distinct IDs in one partition. Threads do not imply a CPU speedup
on interpreters using a GIL. Concurrent CLI processes must use separate output
directories; the requested thread safety applies within each process.

**Approach and rationale:** A single producer reads input once and routes records
using CRC32 of the normalized UTF-8 campaign ID modulo partition count. It owns
every partition writer and closes them before starting aggregation. Each worker
owns one reader, aggregation dictionary, and local Decimal context, then returns
only the union of that partition's top 10 CTR and CPA candidates plus counts.
One coordinator merges candidates and retains at most 20 global candidates.
This is exact because a campaign below its partition's top 10 cannot enter the
global top 10. A process-local lock serializes report staging and replacements.
All worker threads join before temporary directory cleanup, even on failure.

| ID | Acceptance criterion | Verification method |
| --- | --- | --- |
| HP-01 | Same ID always goes to one partition across runs and Python hash seeds; canonical CSV quoting and original error line numbers survive partitioning. | Deterministic routing, quoted-ID, reordered-header, and negative tests |
| HP-02 | CLI uses disk partitioning; `--partitions`, `--workers`, and `--temp-dir` configure it with valid bounds. Empty partitions and header-only input are supported. | CLI and configuration tests; review |
| HP-03 | Worker dictionaries, readers, and Decimal contexts are privately owned; coordinator alone mutates global candidates. Results are identical across worker/partition counts and simultaneous invocations. | Thread ownership review; parallel equivalence and concurrent invocation tests |
| HP-04 | Retain at most 20 candidates per worker result and globally after each merge; output remains identical to the existing independently verified reports. Memory is O(workers × largest partition cardinality + partitions × 20). | Candidate bound tests, skew tests, source review, full-data output hashes |
| HP-05 | A process-local lock prevents concurrent report writers from interleaving; failures retain previous reports where previously guaranteed. | Concurrent writer and existing failure-path tests |
| HP-06 | Each run has a unique workspace; all files close and workers finish before cleanup on success and handled failure. | Workspace, failure, and thread cleanup tests |
| HP-07 | Full dataset actually runs; current measurements are clearly separated from the original single-pass benchmark. Instructions explain disk/memory and thread/process limitations. | Measured benchmark, documentation/link review, human test |

## 2. Plan

- [x] Plan complete

| Order | Work item | Files / components | Dependencies |
| --- | --- | --- | --- |
| 1 | Factor reusable CSV iteration and streaming accumulation; add partition writer and worker summaries | `aggregator.py` | None |
| 2 | Add bounded worker execution, candidate merging, configuration, and report lock | `aggregator.py` | 1 |
| 3 | Add deterministic routing, equivalence, concurrency, isolation, skew, cleanup, and CLI tests | `tests/test_aggregator.py` | 1–2 |
| 4 | Update usage and architecture documentation; preserve the original benchmark as historical evidence | `SOLUTION.md`, challenge `README.md` | 1–3 |
| 5 | Read the complete change and acceptance criteria; fix findings, review again, run tests and full-data benchmark, compare report hashes | Source, tests, reports, benchmark log | 1–4 |
| 6 | Deliver acceptance scenarios and await user results | This record | 5 |

**Verification plan:** Run `python -m unittest discover -s tests -v` from the
challenge directory after review. Tests compare all four totals and both CSVs
against known values and the serial reference, force overlap between workers,
and check data ownership without relying on the GIL. Run
`python benchmark.py --input ad_data.csv --output results/hash-partitioned --partitions 32 --workers 4`
and compare newline-normalized output SHA-256 hashes with the original full-data
reports currently staged in Git. The user replaced working-copy `results/`
reports with example output during this turn; preserve those files. Check
relative documentation links, whitespace, and cleanup.

**Environment / data:** Existing Windows / Python 3.15.2 environment; supplied
1,043,304,870-byte CSV; standard library only. Existing reports have already
passed independent full-data verification in the initial implementation.

**Recovery:** Input stays read-only. Temporary workspaces are unique and cleaned
after all threads finish. Outputs are staged and replaced individually under a
thread lock. An OS failure between the two replacements still is not a file-pair
transaction. Use separate output directories for simultaneous CLI processes.

## 3. Implement

- [x] Implementation complete

**Changes made:** Factored canonical CSV iteration and reusable accumulation;
added CRC32 partitioning, bounded worker execution, top-candidate summaries,
coordinator-only merging, isolated temporary directories, configuration options,
and a process-local report lock. Added concurrency, ownership, configuration,
skew, and cleanup tests. Updated the README and solution guide while preserving
the initial benchmark as historical evidence. Current reports and benchmark
are in `results/hash-partitioned/` and `benchmark-hash-partitioned.txt`.

**Deviations from the plan:** None.

## 4. Code review

- [x] Code review complete; no required fixes remain

**Reviewer / tool:** Codex, separate self-review pass.

**Reviewed scope:** Complete revised `aggregator.py`, all new concurrency tests
and the quoted-ID test update, current documentation, and HP-01–07. Reviewed
the proof for merging local top-10 sets, stable routing, future ownership,
per-thread Decimal contexts, writer-lock scope, original error line mapping,
and workspace cleanup on producer/worker/report failures.

**Findings / resolution:** A consumer-side validation failure could leave a
suspended CSV generator holding a Windows file handle through its exception
traceback. Added explicit `closing()` ownership for input/partition generators
and reviewed the fix before testing. No required findings remain. Worker state
is private, candidate ownership transfers only on completion, and no shared
dictionary updates or report writes rely on the GIL. Cross-process output
coordination and skew limits are documented.

**Final evidence review:** Compared actual full-data stdout with the current
README and solution guide. Verified the new reports' complete normalized content
against fingerprints of the initial independently checked reports. No source
changes followed the 47-test pass. Current measurements are explicitly separate
from the initial baseline; this low-cardinality dataset shows disk/thread
overhead rather than a speed or resident-memory improvement.

## 5. Test

- [x] Required checks passed

| Criterion / case | Command / check | Directory / data | Result | Evidence |
| --- | --- | --- | --- | --- |
| HP-01–06 and existing behavior | `python -m unittest discover -s tests -v` | Challenge directory, Python 3.15.2 / Windows | PASS | 47 tests passed in 3.058 seconds. Includes forced worker overlap, isolated Decimal contexts/workspaces, 8 concurrent report writers, and join-before-cleanup on failure. |
| HP-04,07 | `python benchmark.py --input ad_data.csv --output results/hash-partitioned --partitions 32 --workers 4` (captured with `Tee-Object -FilePath benchmark-hash-partitioned.txt`) | Challenge directory; supplied CSV; Python 3.15.2 / Windows 11 | PASS | 26,843,544 records / 50 campaigns; 171.954 seconds; peak working set 31,592,448 bytes / 30.13 MiB; exit 0 |
| HP-04,06 | Python SHA-256 and workspace check below | Generated reports vs original Git-staged report fingerprints; system temp directory | PASS | Both full CSV contents match after newline normalization; no partition workspaces remain. Working-copy example report hashes are unchanged. |
| Initial documentation check | Python relative-link checker | Repository root, while benchmark was running | FAIL | The new report-directory link did not yet exist; rerun after benchmark completion rather than treating this as a pass. |
| Initial whole-file whitespace check | Python whitespace checker including unchanged challenge README lines | Repository root | FAIL | Flagged the original README's intentional Markdown hard breaks. Preserve original text and check new files plus changed lines instead. |
| HP-07 | `git diff --check`; final Python link/content/whitespace check | Repository root | PASS | Final report directory and linked benchmark exist; current docs were checked against actual measurements. |
| Other platforms / free-threaded runtime | Runtime matrix | Installed environment only | NOT_RUN | Testing targeted the installed Windows Python 3.15.2. Ownership and locking were reviewed to avoid reliance on the GIL; other interpreters and operating systems were not exercised. |

**Remaining issues:** No required automated fixes remain. Human acceptance is
pending. Memory is not capped against partition skew, and the report lock is
process-local; these documented limits are outside the requested scope.

**Baseline report fingerprints:** Before benchmarking, read the original staged
reports with `git show :fv-sec-001-software-engineer-challenge/results/<name>`
using Python subprocess output bytes, replace CRLF with LF, and calculate SHA-256.
Each baseline has 11 lines (header plus 10 campaigns). Working-copy example
reports are deliberately excluded from this comparison.

| Report | Newline-normalized original SHA-256 |
| --- | --- |
| `top10_ctr.csv` | `c8a50e2870b1bf0386818252a8c54a0bdc109469eb0c7ad791f749bd49cd3052` |
| `top10_cpa.csv` | `0bb724eb8ca9237e188e5eb46b5c63ddf24804c1a353668eaf94c81c86c9cedc` |

**Full-data report verification command:** Executed from the challenge directory.

```powershell
@'
import hashlib
from pathlib import Path
import tempfile
expected = {
    'top10_ctr.csv': 'c8a50e2870b1bf0386818252a8c54a0bdc109469eb0c7ad791f749bd49cd3052',
    'top10_cpa.csv': '0bb724eb8ca9237e188e5eb46b5c63ddf24804c1a353668eaf94c81c86c9cedc',
}
for name, original in expected.items():
    data = (Path('results/hash-partitioned') / name).read_bytes().replace(b'\r\n', b'\n')
    actual = hashlib.sha256(data).hexdigest()
    assert actual == original, (name, actual, original)
    assert len(data.splitlines()) == 11
    print(f'PASS: {name}: all content matches the original full-data report; normalized SHA-256 {actual}')
remaining = list(Path(tempfile.gettempdir()).glob('ad-aggregator-*'))
assert not remaining, remaining
print('PASS: full-data temporary workspace cleaned; no ad-aggregator-* directories remain.')
for name in expected:
    actual = hashlib.sha256((Path('results') / name).read_bytes()).hexdigest()
    print(f'Working-copy example report unchanged: {name}: {actual}')
print('aggregator.py SHA-256:', hashlib.sha256(Path('aggregator.py').read_bytes()).hexdigest())
'@ | python -
```

## 6. Human test

- [x] Instructions delivered; status is `AWAITING_HUMAN_TEST`
- [ ] User confirmed all acceptance criteria passed

**Version tested:** Uncommitted hash-partitioned implementation, 2026-10-31.
`aggregator.py` SHA-256:
`24487909d1c09e06b57dc82d9f7028261f833989f72de47898c46ee3c881184b`.
Existing staged user changes were preserved; no commit, push, or staging was
performed by Codex during this revision.

**Setup:** From the repository root, enter
`fv-sec-001-software-engineer-challenge`. Use Python 3.10+.

| ID | Actions | Expected result | Actual result | Status |
| --- | --- | --- | --- | --- |
| HT-HP-01 | Run `python aggregator.py --input tests/fixtures/example.csv --output results/manual-hash --partitions 7 --workers 3`; inspect both CSVs. | CTR IDs CMP001, CMP002, CMP003; CPA IDs CMP001, CMP003, CMP002. CMP001 totals 26000, 640, 93.70, 27; CTR 0.0246 and CPA 3.47. | Not received | PENDING |
| HT-HP-02 | Repeat the example with `--partitions 1 --workers 1` to `results/manual-serial`; compare CSV contents with HT-HP-01. | Both CSVs match exactly. | Not received | PENDING |
| HT-HP-03 | Create an empty scratch directory and run the example with `--temp-dir <scratch-directory>`. Repeat with a copy of the CSV containing `NaN` spend. | Success and failure both leave scratch empty. The invalid row reports its original source path and line; no new reports replace previous good reports. | Not received | PENDING |
| HT-HP-04 | Run `python aggregator.py --input ad_data.csv --output results/manual-full-hash --partitions 32 --workers 4`; compare both CSVs with `results/hash-partitioned/`. | Both match exactly; record/campaign counts are 26,843,544 / 50. | Not received | PENDING |

**Feedback / reproduction steps:** Not received.

**User confirmation:** Not yet confirmed.

## Completion

- [ ] All step exit criteria met; no required fixes remain
- [ ] Human acceptance confirmed
- [ ] Status is `DONE`

**Handoff result:** Hash partitioning and streaming worker aggregation are
implemented, reviewed, and verified with 47 passing tests plus the supplied
1.04 GB dataset. Full-data reports match the initial independently verified
results. Default 32 partitions / 4 threads: 171.954 seconds, 30.13 MiB peak
working set. Run HT-HP-01–04 and report PASS/FAIL. Human acceptance has not been
inferred from existing example files or automated test results.
