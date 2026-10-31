from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
import csv
from datetime import date, timedelta
from decimal import Decimal, localcontext
from fractions import Fraction
import io
from pathlib import Path
import re
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

    def test_default_and_explicit_worker_counts(self):
        self.input.write_text(HEADER + VALID_ROW, encoding="utf-8")
        expected = aggregator.Aggregation()
        with patch.object(aggregator, "PARALLEL_MIN_BYTES", 0), \
             patch.object(aggregator, "_aggregate_parallel", return_value=expected) as parallel:
            self.assertIs(aggregator.aggregate(self.input), expected)
            parallel.assert_called_once_with(self.input, 4)
            parallel.reset_mock()
            self.assertIs(aggregator.aggregate(self.input, workers=2), expected)
            parallel.assert_called_once_with(self.input, 2)
            parallel.reset_mock()
            self.assertEqual(aggregator.aggregate(self.input, workers=1).row_count, 1)
            parallel.assert_not_called()

    def test_small_input_uses_sequential_path_by_default(self):
        self.input.write_text(HEADER + VALID_ROW, encoding="utf-8")
        with patch.object(aggregator, "_aggregate_parallel") as parallel:
            self.assertEqual(aggregator.aggregate(self.input).row_count, 1)
            parallel.assert_not_called()

    def test_cli_passes_default_and_explicit_workers_to_aggregate(self):
        self.input.write_text(HEADER + VALID_ROW, encoding="utf-8")
        for arguments, expected_workers in [([], 4), (["--workers", "12"], 12)]:
            with self.subTest(arguments=arguments), \
                 patch.object(aggregator, "aggregate", return_value=aggregator.Aggregation()) as aggregate, \
                 patch.object(aggregator, "write_reports"), redirect_stdout(io.StringIO()):
                self.assertEqual(aggregator.main([
                    "--input", str(self.input), "--output", str(self.output), *arguments
                ]), 0)
                aggregate.assert_called_once_with(self.input, workers=expected_workers)

    def test_cli_worker_options_produce_expected_reports(self):
        for count in (1, 12):
            with self.subTest(workers=count):
                completed = self.cli(HERE / "fixtures" / "example.csv", None, "--workers", str(count))
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("5 records across 3 campaigns", completed.stdout)
                self.assertEqual([row[0] for row in self.read_report("top10_ctr.csv")[1:]],
                                 ["CMP001", "CMP002", "CMP003"])
                self.assertEqual([row[0] for row in self.read_report("top10_cpa.csv")[1:]],
                                 ["CMP001", "CMP003", "CMP002"])

    def test_cli_rejects_invalid_worker_counts(self):
        self.input.write_text(HEADER + VALID_ROW, encoding="utf-8")
        for arguments in (["--workers", "0"], ["--workers", "-1"],
                          ["--workers", "abc"], ["--workers", "1.5"], ["--workers"]):
            with self.subTest(arguments=arguments):
                completed = self.cli(None, None, *arguments)
                self.assertEqual(completed.returncode, 2)
                self.assertIn("--workers", completed.stderr)
                self.assertNotIn("Traceback", completed.stderr)
                self.assertFalse(self.output.exists())

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

    def test_integer_helper_preserves_surrounding_whitespace_behavior(self):
        self.assertEqual(aggregator.nonnegative_integer("  27  ", "clicks"), 27)
        for value in ["-1", "1.5", "1_000", "１００", " "]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "clicks"):
                aggregator.nonnegative_integer(value, "clicks")

    def test_date_cache_reuses_valid_dates_and_rejects_invalid_dates_each_time(self):
        aggregator.validate_date.cache_clear()
        self.addCleanup(aggregator.validate_date.cache_clear)
        result = self.parse(HEADER + VALID_ROW + VALID_ROW)
        self.assertEqual(result.row_count, 2)
        self.assertEqual(aggregator.validate_date.cache_info().hits, 1)
        self.assertEqual(aggregator.validate_date.cache_info().currsize, 1)
        for invalid_day in ["2025-02-29", "20250101"]:
            invalid = HEADER + VALID_ROW + f"A,{invalid_day},100,10,1.25,2\n"
            for _ in range(2):
                with self.subTest(day=invalid_day), self.assertRaisesRegex(ValueError, "line 3:.*date"):
                    self.parse(invalid)
        self.assertEqual(aggregator.validate_date.cache_info().currsize, 1)

    def test_date_cache_is_bounded_across_repeated_aggregations(self):
        aggregator.validate_date.cache_clear()
        self.addCleanup(aggregator.validate_date.cache_clear)
        start = date(2000, 1, 1)
        rows = [f"A,{(start + timedelta(days=index)).isoformat()},1,1,1,1\n" for index in range(4100)]
        self.assertEqual(self.parse(HEADER + "".join(rows)).row_count, 4100)
        self.assertEqual(aggregator.validate_date.cache_info().maxsize, 4096)
        self.assertLessEqual(aggregator.validate_date.cache_info().currsize, 4096)
        self.assertEqual(self.parse(HEADER + VALID_ROW).row_count, 1)
        self.assertLessEqual(aggregator.validate_date.cache_info().currsize, 4096)

    def test_cached_dates_do_not_change_error_path_or_line_across_files(self):
        aggregator.validate_date.cache_clear()
        self.addCleanup(aggregator.validate_date.cache_clear)
        self.parse(HEADER + VALID_ROW)
        other = self.directory / "other.csv"
        other.write_text(HEADER + VALID_ROW + "A,2025-02-29,1,1,1,1\n", encoding="utf-8")
        with self.assertRaises(ValueError) as raised:
            aggregator.aggregate(other)
        self.assertIn(str(other), str(raised.exception))
        self.assertIn("line 3: date must be a valid YYYY-MM-DD calendar date", str(raised.exception))

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

    def test_line_endings(self):
        for newline in ["\n", "\r\n", "\r"]:
            with self.subTest(newline=newline):
                text = (HEADER + VALID_ROW + VALID_ROW).replace("\n", newline)
                result = self.parse(text)
                self.assertEqual(result.row_count, 2)
                self.assertEqual(result.campaigns["A"].conversions, 4)

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

    def test_quoted_fields_are_rejected(self):
        examples = [
            ('"campaign_id",date,impressions,clicks,spend,conversions\n', "line 1"),
            (HEADER + '"A",2025-01-01,100,10,1.25,2\n', "line 2"),
            (HEADER + VALID_ROW + '"unterminated,2025-01-01,100,10,1.25,2\n', "line 3"),
        ]
        for text, line in examples:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, line + ": quoted"):
                self.parse(text)

    def parallel_input(self, newline="\n"):
        rows = [
            f" C{index % 7} ,2025-01-{index % 28 + 1:02d},{index * 3},{index},{index}.0{index % 10},{index % 4}"
            for index in range(1, 400)
        ]
        rows[50:50] = ["", ""]  # blank records
        text = "﻿" + HEADER + "\n".join(rows) + "\n"
        return text.replace("\n", newline)

    def test_parallel_ranges_match_sequential(self):
        for newline in ["\n", "\r\n"]:
            for workers in [2, 3, 6, 50]:
                with self.subTest(newline=newline, workers=workers):
                    self.parse(self.parallel_input(newline))
                    parallel = aggregator._aggregate_parallel(self.input, workers)
                    self.assertIsNotNone(parallel)
                    self.assertEqual(parallel, aggregator._aggregate_sequential(self.input))

    def test_range_worker_handles_lines_longer_than_a_block(self):
        text = self.parallel_input("\r\n").replace("C3 ", "C3" + " " * 40)
        self.parse(text)
        expected = aggregator._aggregate_sequential(self.input)
        start = len(("﻿" + HEADER).encode())
        end = self.input.stat().st_size
        indexes = list(range(len(aggregator.INPUT_COLUMNS)))
        for block in [1, 7, 64, 4096]:
            with self.subTest(block=block), patch.object(aggregator, "BLOCK_BYTES", block):
                campaigns, row_count = aggregator._aggregate_range(self.input, start, end, indexes)
                self.assertEqual(aggregator.Aggregation(campaigns, row_count), expected)

    def test_concurrent_parallel_calls_do_not_share_data(self):
        inputs = [self.directory / "lf.csv", self.directory / "crlf.csv"]
        inputs[0].write_text(self.parallel_input(), encoding="utf-8", newline="")
        inputs[1].write_text(self.parallel_input("\r\n") + "Z,2025-01-01,9,9,9.99,9\r\n",
                             encoding="utf-8", newline="")
        expected = [aggregator._aggregate_sequential(path) for path in inputs]
        self.assertNotEqual(expected[0], expected[1])
        with patch.object(aggregator, "PARALLEL_MIN_BYTES", 0), ThreadPoolExecutor(8) as pool:
            results = list(pool.map(
                lambda index: aggregator.aggregate(inputs[index % 2], workers=3), range(8)
            ))
        for index, result in enumerate(results):
            self.assertEqual(result, expected[index % 2])
        self.assertEqual(len({id(totals) for result in results for totals in result.campaigns.values()}),
                         sum(len(result.campaigns) for result in results))

    def test_parallel_falls_back_to_sequential_semantics(self):
        examples = {
            "error line": self.parallel_input() + "A,2025-02-30,1,1,1,1\n",
            "quote": self.parallel_input() + '"A",2025-01-01,1,1,1,1\n',
            "bare carriage return": self.parallel_input() + VALID_ROW.replace("\n", "\r") + VALID_ROW,
            "bad header": "campaign_id\n" + self.parallel_input(),
            "invalid encoding": self.parallel_input() + "\udcff",
        }
        for name, text in examples.items():
            with self.subTest(name), patch.object(aggregator, "PARALLEL_MIN_BYTES", 0):
                self.input.write_bytes(text.encode("utf-8", "surrogateescape"))
                self.assertIsNone(aggregator._aggregate_parallel(self.input, 3))
                try:
                    expected = aggregator._aggregate_sequential(self.input)
                except ValueError as error:
                    with self.assertRaisesRegex(ValueError, f"^{re.escape(str(error))}$"):
                        aggregator.aggregate(self.input, workers=3)
                else:
                    self.assertEqual(aggregator.aggregate(self.input, workers=3), expected)

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
