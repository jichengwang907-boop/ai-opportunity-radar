from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.import_external_sources import read_google_trends_exports


class GoogleTrendsImportTests(unittest.TestCase):
    def test_imports_known_terms_from_google_trends_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp)
            (raw_dir / "multiTimeline.csv").write_text(
                "\ufeff类别：所有类别\n"
                "\n"
                "周,ai customer support: (全球),ChatGPT: (全球)\n"
                "2026-05-03,8,80\n"
                "2026-05-10,10,81\n"
                "2026-05-17,12,82\n"
                "2026-05-24,14,83\n",
                encoding="utf-8",
            )

            rows = read_google_trends_exports(
                raw_dir,
                {"ai customer support": "ai customer support"},
                "2026-05-27",
            )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["source"], "google_trends")
        self.assertEqual(row["query"], "ai customer support")
        self.assertEqual(row["result_count"], 11)
        self.assertEqual(row["search_volume"], 14)
        self.assertEqual(row["collected_at"], "2026-05-24")
        self.assertEqual(row["signal_type"], "search_interest")
        self.assertNotIn("ChatGPT", row["title"])

    def test_imports_time_series_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp)
            (raw_dir / "time_series.csv").write_text(
                '"Time","ai invoice processing","ai data entry"\n'
                '"2026-05-10",1,5\n'
                '"2026-05-17",2,7\n'
                '"2026-05-24",3,9\n',
                encoding="utf-8",
            )

            rows = read_google_trends_exports(
                raw_dir,
                {
                    "ai data entry": "ai data entry",
                    "ai invoice processing": "ai invoice processing",
                },
                "2026-05-27",
            )

        self.assertEqual([row["query"] for row in rows], ["ai data entry", "ai invoice processing"])
        self.assertEqual(rows[0]["result_count"], 7)
        self.assertEqual(rows[1]["result_count"], 2)


if __name__ == "__main__":
    unittest.main()
