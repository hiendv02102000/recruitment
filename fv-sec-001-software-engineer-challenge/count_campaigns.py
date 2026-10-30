"""Count CSV records and distinct campaign IDs without loading the file at once."""

import argparse
import csv
from pathlib import Path
from time import perf_counter


def count_campaigns(path: Path) -> tuple[int, int, int]:
    """Return data row count, nonempty campaign ID count, and unique ID count."""
    campaign_ids: set[str] = set()
    row_count = 0
    campaign_id_count = 0

    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.reader(csv_file, strict=True)
        header = next(reader, None)
        if not header or header.count("campaign_id") != 1:
            raise ValueError("CSV must contain exactly one campaign_id column")

        campaign_index = header.index("campaign_id")
        for row in reader:
            if not row:
                continue
            if len(row) != len(header):
                raise ValueError(f"Invalid column count at line {reader.line_num}")

            row_count += 1
            campaign_id = row[campaign_index].strip()
            if campaign_id:
                campaign_id_count += 1
                campaign_ids.add(campaign_id)

    return row_count, campaign_id_count, len(campaign_ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="Count rows and campaign IDs in a CSV file")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).with_name("ad_data.csv"),
        help="CSV file to process (default: ad_data.csv next to this script)",
    )
    args = parser.parse_args()

    start_time = perf_counter()
    try:
        row_count, campaign_id_count, unique_count = count_campaigns(args.input)
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")
    elapsed_seconds = perf_counter() - start_time

    print(f"Data rows (excluding header and empty rows): {row_count:,}")
    print(f"Rows with a campaign_id: {campaign_id_count:,}")
    print(f"Unique campaign_id values: {unique_count:,}")
    print(f"Processing time: {elapsed_seconds:.2f} seconds")


if __name__ == "__main__":
    main()
