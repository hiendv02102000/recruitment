# Ad performance aggregator solution

The [challenge README](README.md) contains the original requirements.
`aggregator.py` implements them with Python's standard library; there are no
third-party dependencies. Use Python 3.10 or newer.

## Setup and run

From the repository root, enter the challenge directory:

```powershell
cd fv-sec-001-software-engineer-challenge
```

If `ad_data.csv` is not extracted yet, download the real archive contents (the
archive is stored using Git LFS), then extract:

```powershell
git lfs pull
python -m zipfile -e ad_data.csv.zip .
```

Run the CLI:

```powershell
python aggregator.py --input ad_data.csv --output results
```

Both file paths are relative to the current working directory. `--input` is
required; `--output` defaults to `results`. Missing output directories are
created automatically. The CLI prints the number of input records, distinct
campaigns, output paths, and processing time. `--help` shows usage.

The [results directory](results/) contains the full-dataset reports:

- `top10_ctr.csv`: at most 10 campaigns, highest CTR first.
- `top10_cpa.csv`: at most 10 campaigns, lowest CPA first; campaigns with no
  conversions are excluded.

Both reports have the columns `campaign_id`, `total_impressions`, `total_clicks`,
`total_spend`, `total_conversions`, `CTR`, and `CPA`.

## Decisions and edge cases

- Read CSV records once and retain only the four totals per distinct campaign.
  Aggregation takes O(rows) time and O(distinct campaigns) memory. Selecting the
  top 10 uses a bounded heap, so it does not sort all campaigns or keep all
  input records. A very large number of distinct campaigns can still use
  substantial memory.
- Inputs of 64 MiB or more are split into newline-aligned byte ranges, one per
  available CPU, and aggregated by worker processes in bounded 1 MiB blocks.
  This is possible because quoted (possibly multiline) fields are rejected.
  Workers share no mutable state: each opens its own file handle and returns
  its own totals, which the calling thread merges after all workers finish.
  Workers start with `forkserver` or `spawn`, never `fork`, so a multithreaded
  caller cannot deadlock, and concurrent `aggregate()` calls are independent.
  If the parallel path meets anything it might treat differently (an invalid
  row, a quote, a bare carriage return, invalid UTF-8, a crashed worker), it
  discards its partial work and reruns the sequential reader, which produces
  the authoritative result or line-numbered error.
- Cache successful canonical-date validations in a bounded 4096-entry LRU
  cache. Invalid dates still fail, and repeated values reuse validation across
  calls. Fields are stripped once before count parsing; Decimal spend handling
  and the public integer helper retain their existing behavior.
- Sum spend with `Decimal`, increasing arithmetic precision when necessary
  to preserve exact sums. Preserve total spend's decimal precision, with a
  minimum of two decimal places. Counts use Python integers.
- Calculate CTR from summed clicks / summed impressions and CPA from summed
  spend / summed conversions. Compare exact fractions for ranking before
  rounding; ties use campaign ID ascending. Display CTR to four decimals and
  CPA to two with half-up rounding. CTR is a ratio, rather than a percentage.
- Zero impressions produce CTR `0.0000`. Zero conversions produce a blank CPA
  cell and exclude the campaign from the CPA report. Fewer than 10 campaigns
  produce fewer than 10 rows. A header-only CSV produces two header-only reports;
  a completely empty file is an error.
- Records are split on plain commas for speed, so CSV quoting is not supported:
  any `"` character is rejected with an error instead of being mis-split.
- Accept UTF-8, an optional BOM, LF/CRLF/CR line endings, blank records, surrounding
  field whitespace, and any ordering of the six required column names. Require
  each column exactly once and reject extra columns. Campaign IDs must be
  nonempty. Dates must be actual calendar dates in `YYYY-MM-DD` form. Counts
  must be nonnegative ASCII integers. Spend must be a finite nonnegative
  decimal; scientific notation is accepted, with adjusted exponent between
  -999999 and 999999. Missing fields, negative values, nonfinite values, bad
  encoding, and quoted fields fail with a readable error. Row errors include
  the source path and physical line number.
- Validate the entire input before writing. Stage both reports before replacing
  existing results, and reject input paths that coincide with a report path.
  Each replacement is atomic; the pair is not transactional if an OS error
  occurs between replacements. Handled staging failures clean temporary files.
  Use a separate output directory to retain earlier reports. Errors exit with
  status 1; invalid CLI arguments use argparse's status 2.

The existing `count_campaigns.py` utility still uses `csv.reader`.

## Correctness checks

Run the tests from the challenge directory:

```powershell
python -m unittest discover -s tests -v
```

The tests check manually calculated results, ranking and the 10-row limit,
unrounded ties, decimal arithmetic, denominator handling, CSV/schema errors,
CLI failures, output preservation, and temporary-file cleanup.

Try the small [example fixture](tests/fixtures/example.csv) independently:

```powershell
python aggregator.py --input tests/fixtures/example.csv --output results/manual-example
```

Expected CTR order: `CMP001`, `CMP002`, `CMP003`. Expected CPA order:
`CMP001`, `CMP003`, `CMP002`. For `CMP001`, totals are 26000 impressions,
640 clicks, 93.70 spend, and 27 conversions; CTR is `0.0246`, CPA is `3.47`.
Complete human acceptance scenarios and verification evidence are in the
[task record](../docs/tasks/csv-aggregator.md).

## Full-dataset benchmark

Run the same CLI through the optional standard-library measurement helper:

```powershell
python benchmark.py --input ad_data.csv --output results
```

`benchmark.py` calls the production CLI in the same process. It measures elapsed
CLI wall time (including parsing and writing, excluding interpreter startup)
and, on Windows, reads the OS-reported process peak working set, including
Python and the helper itself. Other platforms report timing and explicitly
mark memory as unmeasured. Archive extraction is outside the measurement.
This is a single local run; hardware, filesystem cache, interpreter version,
and data cardinality affect the result.

Original single-pass baseline measured on 2026-10-30, before the date-cache
optimization, using the provided extracted dataset:

| Measurement | Result |
| --- | --- |
| Input size | 1,043,304,870 bytes (1.04 GB) |
| Input records / distinct campaigns | 26,843,544 / 50 |
| CLI wall time | 104.581 seconds |
| Peak process working set | 25,477,120 bytes (24.30 MiB) |
| Environment | Windows 11, Python 3.15.2 64-bit, Intel Core i7-10750H |
| Output sizes | 10 campaign rows in each CSV, plus the header |

The command output is preserved in [benchmark-full.txt](benchmark-full.txt).
All 34 automated tests pass. An additional independent full-dataset calculation
uses integer cents to check every emitted total, metric, and ranking; its command
and result are recorded in the [task record](../docs/tasks/csv-aggregator.md).
The supplied CTR report's ten displayed values all round to `0.0275`; ordering
uses the underlying ratios calculated from the integer totals.

### Optimized implementation comparison

On 2026-10-31, three fresh processes per version processed the same
1,043,304,870-byte CSV on Windows 11 / Python 3.15.2, in alternating order.
Each run read all 26,843,544 records and produced reports matching the original
full-data CSVs after CRLF-to-LF normalization. Each process wrote its output to
an isolated temporary directory. The first run may have had a colder filesystem
cache. Interpreter startup and source copying are excluded from CLI wall time.

| Version | Run times (seconds) | Median (seconds) | Median peak working set |
| --- | --- | --- | --- |
| Baseline `850dee4` | 110.686, 113.077, 113.155 | 113.077 | 25,849,856 bytes (24.65 MiB) |
| Optimized | 81.336, 81.421, 79.899 | 81.336 | 25,985,024 bytes (24.78 MiB) |

Median latency fell **28.07%**; median peak working set increased **0.52%**.
The full command output is in [benchmark-latency-comparison.txt](benchmark-latency-comparison.txt),
and the [investigation task record](../docs/tasks/latency-investigation.md)
contains the comparison script and acceptance scenarios. Results vary with the
machine, filesystem cache, interpreter, and dataset.

### Parallel byte-range comparison

On 2026-10-31, on Linux with Python 3.14.4 and a 6-core Intel Core i5-8400,
the same 1,043,304,870-byte CSV was processed by the sequential `str.split`
reader (`346a999`) and the parallel version, alternating. Every run read all
26,843,544 records, and both versions wrote identical reports. Memory is the
peak summed proportional set size (PSS) of the whole process tree, which
counts shared library pages once rather than once per process.

| Version | Run times (seconds) | Peak process-tree PSS |
| --- | --- | --- |
| Sequential `346a999` | 66.04, 62.14, 60.66, 60.97 | 10.5 MiB |
| Parallel, 4 MiB blocks | 14.30, 12.85, 12.08, 13.05, 12.75, 12.66 | 246.8 MiB |
| Parallel, 1 MiB blocks (final) | 12.48, 12.20, 12.15, 12.94 | 96.2–101.6 MiB |

The parallel version is about 5x faster, at the cost of about 90 MiB more
memory for six workers. Smaller blocks cut memory without slowing it down.
An independent reference written in `awk` (no production code) summed every
record in integer cents. A separate checker ranked those totals and confirmed
that all values and the campaign order in both reports match, and that they
match the committed [results](results/) reports.
