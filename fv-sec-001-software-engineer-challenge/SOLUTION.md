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
- Accept UTF-8, an optional BOM, standard CSV quoting, blank records, surrounding
  field whitespace, and any ordering of the six required column names. Require
  each column exactly once and reject extra columns. Campaign IDs must be
  nonempty. Dates must be actual calendar dates in `YYYY-MM-DD` form. Counts
  must be nonnegative ASCII integers. Spend must be a finite nonnegative
  decimal; scientific notation is accepted, with adjusted exponent between
  -999999 and 999999. Missing fields, negative values, nonfinite values, bad
  encoding, and malformed CSV fail with a readable error. Row errors include
  the source path and physical CSV line number (the end line of a quoted
  multiline record).
- Validate the entire input before writing. Stage both reports before replacing
  existing results, and reject input paths that coincide with a report path.
  Each replacement is atomic; the pair is not transactional if an OS error
  occurs between replacements. Handled staging failures clean temporary files.
  Use a separate output directory to retain earlier reports. Errors exit with
  status 1; invalid CLI arguments use argparse's status 2.

The existing `count_campaigns.py` utility is left unchanged.

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

Measured on 2026-10-30, using the provided extracted dataset:

| Measurement | Result |
| --- | --- |
| Input size | 1,043,304,870 bytes (1.04 GB) |
| Input records / distinct campaigns | 26,843,544 / 50 |
| CLI wall time | 104.581 seconds |
| Peak process working set | 25,477,120 bytes (24.30 MiB) |
| Environment | Windows 11, Python 3.15.2 64-bit, Intel Core i7-10750H |
| Output sizes | 10 campaign rows in each CSV, plus the header |

The command output is preserved in [benchmark-full.txt](benchmark-full.txt).
All 30 automated tests pass. An additional independent full-dataset calculation
uses integer cents to check every emitted total, metric, and ranking; its command
and result are recorded in the [task record](../docs/tasks/csv-aggregator.md).
The supplied CTR report's ten displayed values all round to `0.0275`; ordering
uses the underlying ratios calculated from the integer totals.
