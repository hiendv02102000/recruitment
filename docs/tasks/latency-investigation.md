# Brainstorm: Reduce CSV aggregation latency

- Status: `AWAITING_HUMAN_TEST`
- Brainstorm complete: Yes
- Request: "Find solutions to reduce latency"
- Date: 2026-10-31
- Inspected version: `850dee4`, restored single-pass implementation
- Scope: Investigation followed by implementation of the recommended option 1

## Problem, scope, and verified facts

Reduce end-to-end CLI latency while preserving exact spend totals, unrounded
ranking, input validation, original error lines, and existing CSV outputs.
The earlier full-data measurements are 104.581 seconds / 24.30 MiB for the
single-pass version versus 171.954 seconds / 30.13 MiB for the withdrawn
disk-partitioned thread version. Those are historical full-data runs, not fresh
measurements from this investigation.

The installed interpreter is Windows CPython 3.15.2, with the GIL enabled and
12 logical CPUs. DuckDB, Polars, pandas, PyArrow, and NumPy are not installed.
No dependencies were installed during this investigation.

## Experiment and actual results

Used Python's standard library to copy the first **500,000 actual CSV records**
with `csv.reader` / `csv.writer` into a temporary file, preserving CSV record
boundaries. The resulting file was **19,431,404 bytes**. Source extraction was
outside all measured intervals. `cProfile.Profile().runcall(aggregate, sample)`
identified hot functions; separate, unprofiled `perf_counter()` runs measured
each variant three times, alternating variant order. Filesystem cache was warm.
These times cover aggregation, excluding report writing and interpreter startup.

| Variant | Run 1 (s) | Run 2 (s) | Run 3 (s) | Median (s) | Reduction vs sample baseline |
| --- | --- | --- | --- | --- | --- |
| Current single-pass implementation | 2.3647 | 2.3245 | 2.1858 | 2.3245 | Baseline |
| Bounded date-validation cache | 1.8834 | 2.0269 | 1.9238 | 1.9238 | 17.24% |
| Date cache + list unpacking + no repeated stripping in the three count parsers | 1.5895 | 1.5739 | 1.7084 | 1.5895 | 31.62% |

All nine unprofiled runs compared the complete returned `Aggregation` with the
sample baseline, including all four totals for every campaign; all matched.
No experimental full-file speedup, report-writing time, or peak memory was
measured. Do not extrapolate these results into a claimed 1 GB runtime.

The date cache was bounded at 4096 entries. There were **181 distinct dates**
in the sample. Across the six cached runs it reported 181 misses and 2,999,819
hits. It cached the original `date.fromisoformat(value).isoformat()` result;
the existing comparison with the input date remained in place. This experiment
reduced repeated work without intentionally removing validation.

The combined variant used an isolated copy of `aggregate()` compiled from
`inspect.getsource()`: the six-field generator expression became a list
comprehension, and its count parser omitted a second `.strip()` because the
caller had already stripped each field. Spend parsing, exact Decimal addition,
and all other logic remained the original code. Experimental functions existed
only in the temporary Python process. Temporary files were removed.

### Profiling evidence

The profiled baseline took 7.577 seconds and made 17,507,145 calls. Profiling
adds overhead; these numbers locate work and are not benchmark timings.

| Component | Calls on 500,000 rows | Profiled own time (s) | Observation |
| --- | --- | --- | --- |
| `nonnegative_integer` | 1,500,000 | 1.202 | Three Python count-validation calls per row |
| Field-unpacking generator | 3,500,000 | 0.851 | Per-field iteration and generator overhead |
| `decimal_spend` | 500,000 | 0.804 | Decimal syntax and range validation on every row |
| `str.strip` | 5,000,000 | 0.650 | Ten strips per row, including already-stripped values |
| `date.isoformat` | 500,000 | 0.327 | Repeated formatting of only 181 distinct dates |
| Decimal syntax regex | 500,000 | 0.324 | Another potential parsing optimization, not changed here |
| `date.fromisoformat` | 500,000 | 0.118 | Same repeated-date opportunity |
| Dictionary lookup | 500,000 | 0.108 | Campaign lookup is a smaller measured target |

Inference: prioritize validation and row normalization overhead before changing
the aggregation architecture. Only 50 campaigns need final ranking, so final
top-10 selection is not a promising first target.

## Options and recommendation

| Priority | Approach | Evidence / benefit | Tradeoff or correctness condition |
| --- | --- | --- | --- |
| 1 | Keep one input pass; cache validated dates and simplify the row loop | Combined prototype reduced sample latency by 31.62%; standard library only | Keep cache bounded, validate canonical dates before caching, preserve count validation and whitespace behavior; full-data validation still required |
| 2 | Benchmark an integer-cents fast path for ordinary two-decimal spend | May avoid repeated Decimal construction/validation in the common case; not measured | Never convert through float or truncate sub-cent values. Preserve a general Decimal fallback, scientific notation, large exact values, and output precision. Python string parsing could offset any gain. |
| 3 | Benchmark bounded batches with 2–4 worker processes | Processes can run Python work beyond one GIL | Windows startup, pickling, IPC, and higher memory may offset gains. Parent reads complete CSV records; do not split naively on newline bytes. Workers own totals; coordinator alone merges exact results. No disk partition pass. Not benchmarked here. |
| 4 | Optional native CSV/aggregation backend, such as DuckDB | Native parallel CSV reader and grouped SQL aggregation are available | Adds a dependency and different parsing/numeric semantics. DuckDB decimals have a maximum precision of 38, and decimal division returns floating point; preserve final ranking in Python and do not silently narrow the current numeric contract. Not installed or benchmarked here. |

**Recommendation:** Start with option 1. It has measured sample evidence, keeps
the existing memory-efficient streaming structure, avoids new dependencies and
disk traffic, and leaves exact spend arithmetic unchanged. Investigate the cents
fast path only after measuring the remaining bottleneck. Processes/native
execution are later alternatives if the simpler changes do not meet the target.

## Acceptance criteria for a subsequent implementation

1. All existing 30 tests pass, with additional coverage for cached invalid dates,
   bounded cache growth, and repeated invocations if caching is introduced.
2. Full-dataset output contents match the known fingerprints from the current
   task record; preserve exact comparisons, rounding, and validation/error policy.
3. Compare unprofiled baseline/candidate full-data runs under the same conditions;
   report actual runtime and peak working set. Proposed adoption threshold: at
   least 15% lower median runtime with no material memory regression. This is a
   suggested decision gate, not a user-specified or measured full-data outcome.
4. Keep one CSV pass and avoid spill files or new dependencies for option 1.
5. The original standalone brainstorm made no production changes. This follow-up
   is implemented at the user's request; commit or push only when requested.

## Primary references checked

- [Python profiling guidance](https://docs.python.org/3/library/profile.html): profiling locates expensive work; benchmarking should use separate timing runs.
- [Python bounded LRU cache](https://docs.python.org/3/library/functools.html#functools.lru_cache): bounded memoization; cache state is thread-safe, with possible duplicate evaluation of concurrent misses.
- [Python process executor](https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor): bypasses the GIL; functions and values must be picklable.
- [DuckDB CSV reader](https://duckdb.org/docs/stable/data/csv/overview): parallel CSV parsing and explicit column types.
- [DuckDB numeric types](https://duckdb.org/docs/current/sql/data_types/numeric): decimal precision and division semantics.

## Handoff

Investigation completed without changing production source. The user then
requested implementation; the following sections track that work.

## Plan

- [x] Plan complete

Implement option 1: cache only successfully validated canonical dates with a
bounded 4096-entry LRU cache, replace generator-based field unpacking with a
list comprehension, and avoid stripping already-normalized integer fields a
second time while preserving the public helper's existing whitespace behavior.
Keep Decimal arithmetic, original error messages and line numbers, one input
pass, no spill files, and no new dependencies.

1. Update `aggregator.py` and add focused tests for repeated and invalid dates,
   cache bounds, repeated calls, integer whitespace, and existing edge cases.
2. Review the complete diff against the existing behavior and resolve findings.
3. Run the automated suite, then compare the current implementation with the
   committed `850dee4` baseline using three alternating-order full-data runs
   of each version on the same machine. Measure each process's wall time and
   peak working set; compare every output CSV with the verified baseline hashes.
4. Update usage/performance documentation with actual evidence and prepare
   human acceptance instructions. Preserve existing results and benchmark logs.

**Environment:** Windows / Python 3.15.2, the existing 1,043,304,870-byte CSV,
standard library only. Benchmarks use temporary source copies and output
directories to preserve user files; details and raw results will be recorded.

**Decision gate:** Aim for at least 15% lower median full-data latency with no
more than 15% higher median peak working set. This was proposed during the investigation;
if measurements do not meet it, reassess rather than asserting success.

**Human test scenarios prepared before implementation:**

| ID | Action | Expected result | Status |
| --- | --- | --- | --- |
| HT-L01 | From the challenge directory run `python aggregator.py --input tests/fixtures/example.csv --output results/manual-latency`; open both CSVs. | CTR IDs CMP001, CMP002, CMP003; CPA IDs CMP001, CMP003, CMP002; CMP001 totals 26000, 640, 93.70, 27 with CTR 0.0246 and CPA 3.47. | PENDING |
| HT-L02 | Copy `tests/fixtures/example.csv` to `results/manual-latency/bad.csv`; change the second data row's date to `2025-02-29`, then run `python aggregator.py --input results/manual-latency/bad.csv --output results/manual-latency`. | Nonzero exit, source path and line 3 identify an invalid calendar date; previously generated reports remain unchanged. | PENDING |
| HT-L03 | Run `python aggregator.py --input ad_data.csv --output results/manual-latency-full`; compare both output CSVs with the provided `results/` files. | Both reports match; the CLI reports 26,843,544 rows and 50 campaigns. Runtime varies by machine. | PENDING |

**Recovery:** Revert the focused source and test diff if required. Benchmark
outputs are written only to isolated temporary folders; existing reports remain.

## Implement

- [x] Implementation complete

Added a bounded LRU validator for successful canonical dates, changed row
unpacking to a list comprehension, and use a normalized integer parser inside the
hot loop. The original public integer helper still strips whitespace. Added four
tests for cache hits, invalid dates, cache bounds across calls, source/line
errors, and the helper's whitespace behavior. Updated documentation to identify
the earlier full-data measurement as a pre-optimization baseline.

## Code review

- [x] Review complete; no required fixes remain

Reviewer: Codex, separate self-review. Read the complete source/test/README/
solution diff and checked the existing task acceptance criteria. Confirmed the
cached function validates canonical form before returning and exceptions are
not cached; LRU size is bounded and the shared cache is supplied by the standard
library. Count fields are stripped before the private parser is called, while
the original public helper still strips its own input. Decimal arithmetic,
output paths, ranking, error wrapping, and source line reporting are unchanged.
The added tests exercise invalid dates, cache hits and bounds, repeated calls,
and helper compatibility. No required findings; full-file performance and output
equivalence remain to be tested.

**Final evidence review:** After the benchmark, compared all six process results,
report fingerprints, runtime and memory medians, and the README/solution updates
with the captured log. The full-data results satisfy the proposed performance and
memory gate. Production source was not changed after the 34-test run or the
comparison snapshots. No required findings remain.

## Test

- [x] Required checks passed

| Check | Command / context | Result | Evidence |
| --- | --- | --- | --- |
| Original and added behavior | `python -m unittest discover -s tests -v`, challenge directory / Python 3.15.2 | PASS | 34 tests passed in 1.383 seconds |
| Full-data latency, memory, and report equality | Benchmark script below; three alternating-order runs each | PASS | All six runs processed 26,843,544 records / 50 campaigns and both outputs matched the original report hashes. Baseline median 113.077 s and 25,849,856 bytes; optimized median 81.336 s and 25,985,024 bytes. Latency fell 28.07%, peak working set rose 0.52%; proposed gate met. |
| Documentation and diff | `git diff --check` and Python link/content/fingerprint checks from repository root | PASS | 12 relative links resolve; reviewed source hash matches the benchmark snapshot; log records six successful report comparisons and the performance gate; changed-file whitespace checked |

**Full-data benchmark script:** From the challenge directory, execute the Python
code in this block. `850dee4` is the original committed implementation and
report baseline. The script snapshots both implementations and the common
`benchmark.py` helper into a temporary directory; each run reads the same
source CSV and writes its reports into its own temporary output directory. It
checks all report bytes after CRLF-to-LF normalization against the committed
baseline reports. Each process reports its own peak working set. Six fresh
processes run sequentially in alternating order; the first run may have a colder
filesystem cache. Interpreter startup and source copying are outside CLI timing.

```python
# BENCHMARK SCRIPT START
import hashlib
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile

challenge = Path.cwd()
repo = challenge.parent
input_path = (challenge / 'ad_data.csv').resolve(strict=True)
baseline_ref = '850dee4'
prefix = 'fv-sec-001-software-engineer-challenge/'

def committed(path):
    return subprocess.run(
        ['git', 'show', f'{baseline_ref}:{prefix}{path}'],
        cwd=repo, capture_output=True, check=True,
    ).stdout

def digest(data):
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()

expected = {name: digest(committed(f'results/{name}')) for name in ('top10_ctr.csv', 'top10_cpa.csv')}
source = {'baseline': committed('aggregator.py'), 'optimized': (challenge / 'aggregator.py').read_bytes()}
helper = (challenge / 'benchmark.py').read_bytes()
timings = {'baseline': [], 'optimized': []}
peaks = {'baseline': [], 'optimized': []}
order = ['baseline', 'optimized', 'optimized', 'baseline', 'baseline', 'optimized']
print(f'Input: {input_path.stat().st_size:,} bytes; baseline: {baseline_ref}', flush=True)
for name, content in source.items():
    print(f'{name} normalized source SHA-256: {digest(content)}', flush=True)
with tempfile.TemporaryDirectory(prefix='aggregator-comparison-') as scratch:
    scratch = Path(scratch)
    for name, content in source.items():
        directory = scratch / name
        directory.mkdir()
        (directory / 'aggregator.py').write_bytes(content)
        (directory / 'benchmark.py').write_bytes(helper)
    for number, name in enumerate(order, 1):
        output = scratch / f'output-{number}'
        command = [sys.executable, str(scratch / name / 'benchmark.py'), '--input', str(input_path), '--output', str(output)]
        print(f'START {number}/6: {name}', flush=True)
        result = subprocess.run(command, cwd=challenge, text=True, capture_output=True)
        print(result.stdout, end='', flush=True)
        if result.returncode:
            print(result.stderr, file=sys.stderr, flush=True)
            raise RuntimeError(f'{name} benchmark failed with status {result.returncode}')
        assert 'Processed 26,843,544 records across 50 campaigns.' in result.stdout
        seconds = re.search(r'CLI wall time: ([0-9.]+) seconds', result.stdout)
        memory = re.search(r'Peak working set: ([0-9,]+) bytes', result.stdout)
        if not seconds or not memory:
            raise ValueError('Benchmark did not report both wall time and peak working set')
        timings[name].append(float(seconds.group(1)))
        peaks[name].append(int(memory.group(1).replace(',', '')))
        for filename, expected_hash in expected.items():
            actual_hash = digest((output / filename).read_bytes())
            if actual_hash != expected_hash:
                raise ValueError(f'{name} report {filename} differs from baseline: {actual_hash}')
        print(f'PASS {number}/6: {name} reports match both baseline hashes', flush=True)
    baseline_time = statistics.median(timings['baseline'])
    optimized_time = statistics.median(timings['optimized'])
    baseline_peak = statistics.median(peaks['baseline'])
    optimized_peak = statistics.median(peaks['optimized'])
    reduction = (1 - optimized_time / baseline_time) * 100
    memory_change = (optimized_peak / baseline_peak - 1) * 100
    print(f'BASELINE seconds: {timings["baseline"]}; median: {baseline_time:.3f}', flush=True)
    print(f'OPTIMIZED seconds: {timings["optimized"]}; median: {optimized_time:.3f}', flush=True)
    print(f'BASELINE peak bytes: {peaks["baseline"]}; median: {baseline_peak:,}', flush=True)
    print(f'OPTIMIZED peak bytes: {peaks["optimized"]}; median: {optimized_peak:,}', flush=True)
    print(f'MEDIAN latency reduction: {reduction:.2f}%; peak memory change: {memory_change:.2f}%', flush=True)
    print(f'PROPOSED GATE: {"PASS" if reduction >= 15 and memory_change <= 15 else "NOT MET"}', flush=True)
print('Temporary source snapshots and reports cleaned.', flush=True)
# BENCHMARK SCRIPT END
```

Command used from the challenge directory (output captured in
`benchmark-latency-comparison.txt`):

```powershell
python -u -c "from pathlib import Path; t = Path('../docs/tasks/latency-investigation.md').read_text(encoding='utf-8'); s = t.split('# BENCHMARK SCRIPT START\n', 1)[1].split('\n# BENCHMARK SCRIPT END', 1)[0]; exec(compile(s, '<benchmark-script>', 'exec'))" | Tee-Object -FilePath benchmark-latency-comparison.txt
```

## Human test

- [x] Instructions delivered; status `AWAITING_HUMAN_TEST`
- [ ] User confirmed all acceptance criteria passed

**Version:** Optimized `aggregator.py`, normalized SHA-256
`95dd15b48dc7b7ebc638f7aca7e0ff532666081b7a770824429254cb14075c0d`.
All 34 tests passed and all six full-data runs matched the original report
fingerprints. HT-L01–03 above are ready for the user; actual results and user
confirmation have not been received. The user explicitly requested a commit;
that request does not imply human acceptance. A push requires a separate request.
