"""Stream advertising records into exact per-campaign totals and ranked CSVs."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, DecimalException, Inexact, localcontext
from fractions import Fraction
from functools import lru_cache
from heapq import nsmallest
from itertools import repeat
import multiprocessing
import os
from pathlib import Path
import re
import tempfile
from time import perf_counter


INPUT_COLUMNS = (
    "campaign_id", "date", "impressions", "clicks", "spend", "conversions"
)
OUTPUT_COLUMNS = (
    "campaign_id", "total_impressions", "total_clicks", "total_spend",
    "total_conversions", "CTR", "CPA",
)
REPORT_NAMES = ("top10_ctr.csv", "top10_cpa.csv")
DEFAULT_WORKERS = 4
# Smaller inputs are not worth the worker start-up cost.
PARALLEL_MIN_BYTES = 64 * 1024 * 1024
BLOCK_BYTES = 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
DECIMAL_TEXT = re.compile(
    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z"
)


@dataclass(slots=True)
class CampaignTotals:
    impressions: int = 0
    clicks: int = 0
    spend: Decimal = Decimal(0)
    conversions: int = 0


@dataclass(slots=True)
class Aggregation:
    campaigns: dict[str, CampaignTotals] = field(default_factory=dict)
    row_count: int = 0


def nonnegative_integer(value: str, column: str) -> int:
    """Parse a count while accepting surrounding whitespace."""
    return _nonnegative_integer(value.strip(), column)


def _nonnegative_integer(value: str, column: str) -> int:
    """Parse a count whose surrounding whitespace has already been stripped."""
    if not value or not value.isascii() or not value.isdecimal():
        raise ValueError(f"{column} must be a nonnegative integer")
    return int(value)


@lru_cache(maxsize=4096)
def validate_date(value: str) -> None:
    """Cache successful, canonical calendar-date validations only."""
    if date.fromisoformat(value).isoformat() != value:
        raise ValueError


def decimal_spend(value: str) -> Decimal:
    value = value.strip()
    if not DECIMAL_TEXT.fullmatch(value):
        raise ValueError("spend must be a finite nonnegative decimal")
    spend = Decimal(value)
    if not spend.is_finite() or spend < 0:
        raise ValueError("spend must be a finite nonnegative decimal")
    if not -999999 <= spend.adjusted() <= 999999:
        raise ValueError("spend exponent is outside the supported decimal range")
    return spend


def add_spend(context, total: Decimal, spend: Decimal) -> Decimal:
    """Add exactly, growing precision only when needed rather than rounding."""
    try:
        return total + spend
    except Inexact:
        context.prec = (
            max(total.adjusted(), spend.adjusted())
            - min(total.as_tuple().exponent, spend.as_tuple().exponent)
            + 2
        )
        return total + spend


def column_indexes(line: str) -> list[int]:
    """Validate a header line and return the position of each input column."""
    if '"' in line:
        raise ValueError("quoted CSV fields are not supported")
    header = line.rstrip("\r\n").split(",")
    if len(header) != len(INPUT_COLUMNS) or set(header) != set(INPUT_COLUMNS):
        raise ValueError(
            "expected exactly these CSV columns, once each: " + ", ".join(INPUT_COLUMNS)
        )
    return [header.index(column) for column in INPUT_COLUMNS]


def accumulate(lines, first_line: int, indexes: list[int],
               campaigns: dict[str, CampaignTotals], context) -> int:
    """Add each record to campaigns and return the record count.

    Plain comma splitting is faster than csv.reader but cannot parse quoting,
    so quoted fields are rejected rather than silently split apart.
    """
    row_count = 0
    line_number = first_line
    try:
        for line_number, line in enumerate(lines, first_line):
            if '"' in line:
                raise ValueError("quoted CSV fields are not supported")
            line = line.rstrip("\n")
            if not line:
                continue
            row = line.split(",")
            if len(row) != len(INPUT_COLUMNS):
                raise ValueError(f"expected {len(INPUT_COLUMNS)} fields, got {len(row)}")
            campaign_id, day, raw_impressions, raw_clicks, raw_spend, raw_conversions = [
                row[index].strip() for index in indexes
            ]
            if not campaign_id:
                raise ValueError("campaign_id must not be empty")
            try:
                validate_date(day)
            except ValueError:
                raise ValueError("date must be a valid YYYY-MM-DD calendar date") from None
            # Avoid a Python helper call for valid counts; retain its error path.
            impressions = (int(raw_impressions) if raw_impressions.isascii() and raw_impressions.isdecimal()
                           else _nonnegative_integer(raw_impressions, "impressions"))
            clicks = (int(raw_clicks) if raw_clicks.isascii() and raw_clicks.isdecimal()
                      else _nonnegative_integer(raw_clicks, "clicks"))
            spend = decimal_spend(raw_spend)
            conversions = (int(raw_conversions) if raw_conversions.isascii() and raw_conversions.isdecimal()
                           else _nonnegative_integer(raw_conversions, "conversions"))

            totals = campaigns.get(campaign_id)
            if totals is None:
                totals = campaigns[campaign_id] = CampaignTotals()
            new_spend = add_spend(context, totals.spend, spend)
            totals.impressions += impressions
            totals.clicks += clicks
            totals.spend = new_spend
            totals.conversions += conversions
            row_count += 1
    except (ValueError, UnicodeError, DecimalException) as error:
        raise ValueError(f"line {line_number}: {error}") from error
    return row_count


def aggregate(input_path: Path, workers: int | None = None) -> Aggregation:
    """Read once, retaining only totals for each distinct campaign.

    Large inputs are split into byte ranges aggregated by worker processes.
    Anything the parallel path cannot handle identically falls back to the
    sequential path, which also produces the authoritative error message.
    """
    if workers is None:
        workers = DEFAULT_WORKERS
    try:
        size = input_path.stat().st_size
    except OSError:
        size = 0  # Let the sequential open report the error.
    if workers > 1 and size >= PARALLEL_MIN_BYTES:
        result = _aggregate_parallel(input_path, workers)
        if result is not None:
            return result
    return _aggregate_sequential(input_path)


def _aggregate_sequential(input_path: Path) -> Aggregation:
    result = Aggregation()
    with input_path.open(encoding="utf-8-sig") as source, localcontext() as context:
        context.traps[Inexact] = True
        try:
            line = source.readline()
            if not line:
                raise ValueError("empty file: expected a CSV header")
            indexes = column_indexes(line)
        except (ValueError, UnicodeError) as error:
            raise ValueError(f"{input_path}: line 1: {error}") from error
        try:
            result.row_count = accumulate(source, 2, indexes, result.campaigns, context)
        except ValueError as error:
            raise ValueError(f"{input_path}: {error}") from error
    return result


def _aggregate_parallel(input_path: Path, workers: int) -> Aggregation | None:
    """Aggregate newline-aligned byte ranges; None means use the sequential path."""
    with input_path.open("rb") as source:
        header = source.readline(MAX_LINE_BYTES)
        if not header.endswith(b"\n") or b"\r" in header.rstrip(b"\r\n"):
            return None
        try:
            indexes = column_indexes(header.decode("utf-8-sig"))
        except ValueError:
            return None
        bounds = [source.tell()]
        size = source.seek(0, os.SEEK_END)
        for part in range(1, workers):
            source.seek(max(bounds[0] + (size - bounds[0]) * part // workers, bounds[-1]))
            line = source.readline(MAX_LINE_BYTES)
            if line and not line.endswith(b"\n"):
                return None
            bounds.append(source.tell())
        bounds.append(size)
    ranges = [(start, end) for start, end in zip(bounds, bounds[1:]) if start < end]
    if not ranges:
        return None
    # Workers share no mutable state: each opens its own file handle and owns its
    # totals, which this thread merges only after every worker has finished.
    # Forking a multithreaded caller can deadlock, so never use "fork".
    methods = multiprocessing.get_all_start_methods()
    mp_context = multiprocessing.get_context("forkserver" if "forkserver" in methods else "spawn")
    try:
        with ProcessPoolExecutor(len(ranges), mp_context=mp_context) as pool:
            parts = list(pool.map(
                _aggregate_range, repeat(input_path), *zip(*ranges), repeat(indexes)
            ))
    except (ValueError, BrokenProcessPool):
        return None
    result = Aggregation()
    with localcontext() as context:
        context.traps[Inexact] = True
        for campaigns, row_count in parts:
            result.row_count += row_count
            for campaign_id, part in campaigns.items():
                totals = result.campaigns.get(campaign_id)
                if totals is None:
                    result.campaigns[campaign_id] = part
                    continue
                totals.impressions += part.impressions
                totals.clicks += part.clicks
                totals.spend = add_spend(context, totals.spend, part.spend)
                totals.conversions += part.conversions
    return result


def _aggregate_range(input_path: Path, start: int, end: int,
                     indexes: list[int]) -> tuple[dict[str, CampaignTotals], int]:
    """Worker: aggregate the complete lines in [start, end) in bounded blocks.

    Raises ValueError for anything the sequential path might treat differently.
    """
    campaigns: dict[str, CampaignTotals] = {}
    row_count = 0
    with input_path.open("rb") as source, localcontext() as context:
        context.traps[Inexact] = True
        source.seek(start)
        remaining = end - start
        pending = b""
        while remaining:
            block = source.read(min(BLOCK_BYTES, remaining))
            if not block:
                raise ValueError("input changed while reading")
            remaining -= len(block)
            data = pending + block
            # Keep a trailing partial line, even one spanning several blocks.
            cut = len(data) if not remaining else data.rfind(b"\n") + 1
            data, pending = data[:cut], data[cut:]
            text = data.decode("utf-8")
            if "\r" in text:
                # Bare carriage returns are line breaks for the sequential reader.
                text = text.replace("\r\n", "\n")
                if "\r" in text:
                    raise ValueError("bare carriage return")
            row_count += accumulate(text.split("\n"), 1, indexes, campaigns, context)
    return campaigns, row_count


def ctr(totals: CampaignTotals) -> Fraction:
    return Fraction(totals.clicks, totals.impressions) if totals.impressions else Fraction(0)


def top_campaigns(campaigns: dict[str, CampaignTotals]) -> tuple[list, list]:
    """Rank exact ratios; ID order makes equal-ratio results deterministic."""
    by_ctr = nsmallest(10, campaigns.items(), key=lambda item: (-ctr(item[1]), item[0]))
    by_cpa = nsmallest(
        10,
        ((key, totals) for key, totals in campaigns.items() if totals.conversions),
        key=lambda item: (Fraction(item[1].spend) / item[1].conversions, item[0]),
    )
    return by_ctr, by_cpa


def rounded_ratio(value: Fraction, places: int) -> str:
    """Format a nonnegative exact ratio using decimal half-up rounding."""
    scale = 10 ** places
    rounded = (2 * value.numerator * scale + value.denominator) // (2 * value.denominator)
    return f"{rounded // scale}.{rounded % scale:0{places}d}"


def report_row(campaign_id: str, totals: CampaignTotals) -> tuple:
    spend_text = format(totals.spend, "f")
    whole, _, decimals = spend_text.partition(".")
    spend_text = whole + "." + decimals.ljust(2, "0")
    return (
        campaign_id, totals.impressions, totals.clicks, spend_text, totals.conversions,
        rounded_ratio(ctr(totals), 4),
        rounded_ratio(Fraction(totals.spend) / totals.conversions, 2)
        if totals.conversions else "",
    )


def write_reports(campaigns: dict[str, CampaignTotals], output_dir: Path) -> None:
    """Stage both CSVs, then replace each destination; clean up temporary files."""
    rankings = top_campaigns(campaigns)
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = [output_dir / name for name in REPORT_NAMES]
    for target in targets:
        if target.is_dir():
            raise IsADirectoryError(f"report destination is a directory: {target}")
    staged: list[tuple[Path, Path]] = []
    try:
        for target, ranking in zip(targets, rankings):
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="", dir=output_dir,
                prefix=f".{target.stem}-", suffix=".tmp", delete=False,
            ) as destination:
                staged.append((Path(destination.name), target))
                writer = csv.writer(destination)
                writer.writerow(OUTPUT_COLUMNS)
                writer.writerows(report_row(key, totals) for key, totals in ranking)
            # On Windows the temporary file must be closed before replacement.
        for temporary, target in staged:
            temporary.replace(target)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def positive_worker_count(value: str) -> int:
    try:
        count = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer") from None
    if count < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="UTF-8 advertising CSV")
    parser.add_argument("--output", type=Path, default=Path("results"), help="report directory (default: results)")
    parser.add_argument("--workers", type=positive_worker_count, default=DEFAULT_WORKERS,
                        help=f"worker processes for large inputs (default: {DEFAULT_WORKERS})")
    args = parser.parse_args(argv)
    start = perf_counter()
    try:
        if any(args.input.resolve() == (args.output / name).resolve() for name in REPORT_NAMES):
            raise ValueError("input must not be one of the output report paths")
        result = aggregate(args.input, workers=args.workers)
        write_reports(result.campaigns, args.output)
    except (OSError, ValueError, UnicodeError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"Processed {result.row_count:,} records across {len(result.campaigns):,} campaigns.")
    for name in REPORT_NAMES:
        print(f"Wrote {args.output / name}")
    print(f"Processing time: {perf_counter() - start:.2f} seconds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
