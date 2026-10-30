import csv
from decimal import Decimal, localcontext
from fractions import Fraction
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import aggregator


HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "aggregator.py"
HEADER = ",".join(aggregator.INPUT_COLUMNS) + "\n"
VALID_ROW = "A,2025-01-01,100,10,1.25,2\n"


class AggregatorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.input = self.directory / "input.csv"
        self.output = self.directory / "reports"

    def parse(self, text):
        self.input.write_text(text, encoding="utf-8", newline="")
        return aggregator.aggregate(self.input)

    def cli(self, input_path=None, output_path=None, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--input", str(input_path or self.input),
             "--output", str(output_path or self.output), *extra],
            capture_output=True, text=True, timeout=20,
        )

    def read_report(self, name):
        with (self.output / name).open(encoding="utf-8", newline="") as source:
            return list(csv.reader(source))

    def test_example_totals(self):
        result = aggregator.aggregate(HERE / "fixtures" / "example.csv")
        self.assertEqual(result.row_count, 5)
        self.assertEqual(len(result.campaigns), 3)
        self.assertEqual(result.campaigns["CMP001"], aggregator.CampaignTotals(26000, 640, Decimal("93.70"), 27))
        self.assertEqual(result.campaigns["CMP002"], aggregator.CampaignTotals(16500, 270, Decimal("59.00"), 9))
        self.assertEqual(result.campaigns["CMP003"], aggregator.CampaignTotals(5000, 60, Decimal("15.00"), 3))

    def test_example_cli_csv_values_and_order(self):
        completed = self.cli(HERE / "fixtures" / "example.csv")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("5 records across 3 campaigns", completed.stdout)
        self.assertEqual(completed.stderr, "")
        header = list(aggregator.OUTPUT_COLUMNS)
        one = ["CMP001", "26000", "640", "93.70", "27", "0.0246", "3.47"]
        two = ["CMP002", "16500", "270", "59.00", "9", "0.0164", "6.56"]
        three = ["CMP003", "5000", "60", "15.00", "3", "0.0120", "5.00"]
        self.assertEqual(self.read_report("top10_ctr.csv"), [header, one, two, three])
        self.assertEqual(self.read_report("top10_cpa.csv"), [header, one, three, two])

    def test_reordered_header_bom_blank_rows_and_whitespace(self):
        result = self.parse(
            "\ufeffspend,clicks,date,campaign_id,conversions,impressions\n\n"
            " 1.25 , 10 ,2024-02-29, A , 2 , 100 \n\n"
        )
        self.assertEqual(result.row_count, 1)
        self.assertEqual(result.campaigns["A"], aggregator.CampaignTotals(100, 10, Decimal("1.25"), 2))

    def test_zero_denominators_and_no_eligible_cpa(self):
        result = self.parse(HEADER + "ZERO,2025-01-01,0,7,0,0\n")
        aggregator.write_reports(result.campaigns, self.output)
        self.assertEqual(self.read_report("top10_ctr.csv")[1], ["ZERO", "0", "7", "0.00", "0", "0.0000", ""])
        self.assertEqual(self.read_report("top10_cpa.csv"), [list(aggregator.OUTPUT_COLUMNS)])

    def test_zero_conversions_excluded_only_from_cpa(self):
        result = self.parse(HEADER + "ZERO,2025-01-01,1,1,5,0\n" + VALID_ROW)
        ctr, cpa = aggregator.top_campaigns(result.campaigns)
        self.assertEqual([key for key, _ in ctr], ["ZERO", "A"])
        self.assertEqual([key for key, _ in cpa], ["A"])

    def test_header_only_writes_empty_reports(self):
        result = self.parse(HEADER + "\n")
        self.assertEqual(result.row_count, 0)
        aggregator.write_reports(result.campaigns, self.output)
        for name in aggregator.REPORT_NAMES:
            self.assertEqual(self.read_report(name), [list(aggregator.OUTPUT_COLUMNS)])

    def test_top_ten_boundaries(self):
        rows = [f"C{i:02},2025-01-01,100,{i},{i},1\n" for i in range(12)]
        result = self.parse(HEADER + "".join(rows))
        ctr, cpa = aggregator.top_campaigns(result.campaigns)
        self.assertEqual([key for key, _ in ctr], [f"C{i:02}" for i in range(11, 1, -1)])
        self.assertEqual([key for key, _ in cpa], [f"C{i:02}" for i in range(10)])

    def test_ties_use_id_at_tenth_place(self):
        rows = [f"C{i:02},2025-01-01,100,10,2,1\n" for i in range(11, -1, -1)]
        result = self.parse(HEADER + "".join(rows))
        for ranking in aggregator.top_campaigns(result.campaigns):
            self.assertEqual([key for key, _ in ranking], [f"C{i:02}" for i in range(10)])

    def test_sorting_uses_unrounded_ratios(self):
        result = self.parse(
            HEADER + "A,2025-01-01,1000000,10000,1.004,1\n"
            + "Z,2025-01-01,1000000,10001,1.003,1\n"
        )
        for ranking in aggregator.top_campaigns(result.campaigns):
            self.assertEqual([key for key, _ in ranking], ["Z", "A"])

    def test_sorting_does_not_lose_precision_for_large_integers(self):
        big = 10 ** 40
        campaigns = {
            "A": aggregator.CampaignTotals(big, big - 1, Decimal("1.000000000000000000000000000002"), 1),
            "Z": aggregator.CampaignTotals(big, big, Decimal("1.000000000000000000000000000001"), 1),
        }
        for ranking in aggregator.top_campaigns(campaigns):
            self.assertEqual([key for key, _ in ranking], ["Z", "A"])

    def test_decimal_sums_preserve_subcent_precision(self):
        result = self.parse(
            HEADER + "A,2025-01-01,1,1,0.1,1\n"
            + "A,2025-01-01,1,1,0.2,1\n"
            + "A,2025-01-01,1,1,0.003,1\n"
        )
        self.assertEqual(result.campaigns["A"].spend, Decimal("0.303"))
        self.assertEqual(aggregator.report_row("A", result.campaigns["A"])[3], "0.303")

    def test_spend_precision_grows_without_rounding_or_changing_callers_context(self):
        with localcontext() as context:
            context.prec = 5
            result = self.parse(
                HEADER + "A,2025-01-01,1,1,123456789012345678901234567890,1\n"
                + "A,2025-01-01,1,1,0.000000000000000000000000000001,1\n"
            )
            self.assertEqual(context.prec, 5)
        self.assertEqual(result.campaigns["A"].spend, Decimal("123456789012345678901234567890.000000000000000000000000000001"))

    def test_scientific_decimal_notation(self):
        result = self.parse(HEADER + "A,2025-01-01,1,1,1.25e2,1\n")
        self.assertEqual(aggregator.report_row("A", result.campaigns["A"])[3], "125.00")

    def test_half_up_rounding_and_fraction_format(self):
        self.assertEqual(aggregator.rounded_ratio(Fraction(1, 20000), 4), "0.0001")
        self.assertEqual(aggregator.rounded_ratio(Fraction(201, 200), 2), "1.01")
        self.assertEqual(aggregator.rounded_ratio(Fraction(1, 3), 4), "0.3333")
        self.assertEqual(aggregator.rounded_ratio(Fraction(19999, 20000), 4), "1.0000")

    def test_quoted_ids_round_trip(self):
        for newline in ["\n", "\r\n"]:
            with self.subTest(newline=newline):
                campaign = f'comma, quote" and{newline}newline'
                buffer = io.StringIO(newline="")
                writer = csv.writer(buffer)
                writer.writerow(aggregator.INPUT_COLUMNS)
                writer.writerow([campaign, "2025-01-01", 100, 10, "1.25", 2])
                result = self.parse(buffer.getvalue())
                aggregator.write_reports(result.campaigns, self.output)
                self.assertEqual(self.read_report("top10_ctr.csv")[1][0], campaign)

    def test_invalid_headers(self):
        headers = [
            "", "\n", "campaign_id,date\n", HEADER.replace("spend", "clicks"),
            HEADER.rstrip() + ",extra\n",
        ]
        for header in headers:
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, "line 1"):
                self.parse(header)

    def test_invalid_rows_report_line_and_reason(self):
        examples = [
            ("A,2025-01-01,100,10,1.25\n", "fields"),
            ("A,2025-01-01,100,10,1.25,2,extra\n", "fields"),
            (" ,2025-01-01,100,10,1.25,2\n", "campaign_id"),
            ("A,2025-02-29,100,10,1.25,2\n", "date"),
            ("A,20250101,100,10,1.25,2\n", "date"),
            ("A,2025-01-01,-1,10,1.25,2\n", "impressions"),
            ("A,2025-01-01,100,1.5,1.25,2\n", "clicks"),
            ("A,2025-01-01,100,10,1.25,\n", "conversions"),
            ("A,2025-01-01,1_000,10,1.25,2\n", "impressions"),
            ("A,2025-01-01,１００,10,1.25,2\n", "impressions"),
        ]
        for row, reason in examples:
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, "line 3:.*" + reason):
                self.parse(HEADER + VALID_ROW + row)

    def test_invalid_spend(self):
        for spend in ["NaN", "Infinity", "-1", "abc", "", "1_000", "1e9999999", "1e-9999999"]:
            with self.subTest(spend=spend), self.assertRaisesRegex(ValueError, "line 2:.*spend"):
                self.parse(HEADER + f"A,2025-01-01,100,10,{spend},2\n")

    def test_malformed_csv(self):
        with self.assertRaisesRegex(ValueError, "line 2"):
            self.parse(HEADER + '"unterminated,2025-01-01,100,10,1.25,2\n')

    def test_invalid_encoding_exits_without_traceback(self):
        self.input.write_bytes(HEADER.encode() + b"\xff")
        completed = self.cli()
        self.assertEqual(completed.returncode, 1)
        self.assertIn("Error:", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        self.assertFalse(self.output.exists())

    def test_invalid_input_preserves_existing_reports(self):
        self.output.mkdir()
        for name in aggregator.REPORT_NAMES:
            (self.output / name).write_text("previous report", encoding="utf-8")
        self.input.write_text(HEADER + VALID_ROW + "A,bad,1,1,1,1\n", encoding="utf-8")
        completed = self.cli()
        self.assertEqual(completed.returncode, 1)
        self.assertIn("line 3", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        for name in aggregator.REPORT_NAMES:
            self.assertEqual((self.output / name).read_text(), "previous report")
        self.assertEqual(len(list(self.output.iterdir())), 2)

    def test_missing_input(self):
        completed = self.cli()
        self.assertEqual(completed.returncode, 1)
        self.assertIn("Error:", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        self.assertFalse(self.output.exists())

    def test_directory_as_input(self):
        completed = self.cli(self.directory)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("Error:", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)

    def test_output_directory_is_a_file(self):
        self.input.write_text(HEADER + VALID_ROW, encoding="utf-8")
        self.output.write_text("keep me", encoding="utf-8")
        completed = self.cli()
        self.assertEqual(completed.returncode, 1)
        self.assertNotIn("Traceback", completed.stderr)
        self.assertEqual(self.output.read_text(), "keep me")

    def test_input_cannot_be_a_report_destination(self):
        self.output.mkdir()
        for name in aggregator.REPORT_NAMES:
            input_path = self.output / name
            input_path.write_text(HEADER + VALID_ROW, encoding="utf-8")
            with self.subTest(name=name):
                completed = self.cli(input_path)
                self.assertEqual(completed.returncode, 1)
                self.assertIn("input must not", completed.stderr)
                self.assertEqual(input_path.read_text(), HEADER + VALID_ROW)

    def test_directory_as_report_fails_before_replacing_other_report(self):
        self.output.mkdir()
        (self.output / "top10_ctr.csv").write_text("keep me", encoding="utf-8")
        (self.output / "top10_cpa.csv").mkdir()
        result = self.parse(HEADER + VALID_ROW)
        with self.assertRaises(IsADirectoryError):
            aggregator.write_reports(result.campaigns, self.output)
        self.assertEqual((self.output / "top10_ctr.csv").read_text(), "keep me")

    def test_staging_failure_preserves_reports_and_cleans_temporary_files(self):
        self.output.mkdir()
        for name in aggregator.REPORT_NAMES:
            (self.output / name).write_text("keep me", encoding="utf-8")
        result = self.parse(HEADER + VALID_ROW)
        original = aggregator.report_row
        calls = 0

        def fail_second_report(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated write failure")
            return original(*args)

        with patch.object(aggregator, "report_row", side_effect=fail_second_report):
            with self.assertRaisesRegex(OSError, "simulated write failure"):
                aggregator.write_reports(result.campaigns, self.output)
        self.assertEqual(sorted(path.name for path in self.output.iterdir()), sorted(aggregator.REPORT_NAMES))
        for name in aggregator.REPORT_NAMES:
            self.assertEqual((self.output / name).read_text(), "keep me")

    def test_success_replaces_reports_and_leaves_no_temporary_files(self):
        self.output.mkdir()
        for name in aggregator.REPORT_NAMES:
            (self.output / name).write_text("old", encoding="utf-8")
        self.input.write_text(HEADER + VALID_ROW, encoding="utf-8")
        completed = self.cli()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(sorted(path.name for path in self.output.iterdir()), sorted(aggregator.REPORT_NAMES))
        for name in aggregator.REPORT_NAMES:
            self.assertEqual(self.read_report(name)[1], ["A", "100", "10", "1.25", "2", "0.1000", "0.63"])

    def test_default_output_directory(self):
        self.input.write_text(HEADER + VALID_ROW, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--input", str(self.input)],
            cwd=self.directory, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue((self.directory / "results" / "top10_ctr.csv").is_file())

    def test_help_and_required_argument(self):
        for arguments, returncode in [(["--help"], 0), ([], 2)]:
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), *arguments],
                capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(completed.returncode, returncode)
            self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
