"""Stream advertising records into exact per-campaign totals and ranked CSVs."""

import argparse
import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, DecimalException, Inexact, localcontext
from fractions import Fraction
from heapq import nsmallest
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
    value = value.strip()
    if not value or not value.isascii() or not value.isdecimal():
        raise ValueError(f"{column} must be a nonnegative integer")
    return int(value)


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


def aggregate(input_path: Path) -> Aggregation:
    """Read once, retaining only totals for each distinct campaign."""
    result = Aggregation()
    with input_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, strict=True)
        with localcontext() as context:
            # Grow precision only when needed, rather than silently rounding sums.
            context.traps[Inexact] = True
            try:
                header = next(reader, None)
                if header is None:
                    raise ValueError("empty file: expected a CSV header")
                if len(header) != len(INPUT_COLUMNS) or set(header) != set(INPUT_COLUMNS):
                    raise ValueError(
                        "expected exactly these CSV columns, once each: "
                        + ", ".join(INPUT_COLUMNS)
                    )
                indexes = [header.index(column) for column in INPUT_COLUMNS]
                for row in reader:
                    if not row:
                        continue
                    if len(row) != len(header):
                        raise ValueError(f"expected {len(header)} fields, got {len(row)}")
                    campaign_id, day, raw_impressions, raw_clicks, raw_spend, raw_conversions = (
                        row[index].strip() for index in indexes
                    )
                    if not campaign_id:
                        raise ValueError("campaign_id must not be empty")
                    try:
                        if date.fromisoformat(day).isoformat() != day:
                            raise ValueError
                    except ValueError:
                        raise ValueError("date must be a valid YYYY-MM-DD calendar date") from None
                    impressions = nonnegative_integer(raw_impressions, "impressions")
                    clicks = nonnegative_integer(raw_clicks, "clicks")
                    spend = decimal_spend(raw_spend)
                    conversions = nonnegative_integer(raw_conversions, "conversions")

                    totals = result.campaigns.get(campaign_id)
                    if totals is None:
                        totals = result.campaigns[campaign_id] = CampaignTotals()
                    try:
                        new_spend = totals.spend + spend
                    except Inexact:
                        context.prec = (
                            max(totals.spend.adjusted(), spend.adjusted())
                            - min(totals.spend.as_tuple().exponent, spend.as_tuple().exponent)
                            + 2
                        )
                        new_spend = totals.spend + spend
                    totals.impressions += impressions
                    totals.clicks += clicks
                    totals.spend = new_spend
                    totals.conversions += conversions
                    result.row_count += 1
            except (ValueError, csv.Error, UnicodeError, DecimalException) as error:
                raise ValueError(
                    f"{input_path}: line {max(reader.line_num, 1)}: {error}"
                ) from error
    return result


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="UTF-8 advertising CSV")
    parser.add_argument("--output", type=Path, default=Path("results"), help="report directory (default: results)")
    args = parser.parse_args(argv)
    start = perf_counter()
    try:
        if any(args.input.resolve() == (args.output / name).resolve() for name in REPORT_NAMES):
            raise ValueError("input must not be one of the output report paths")
        result = aggregate(args.input)
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
