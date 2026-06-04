from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from shopping_intel.opportunity import apply_opportunity_trends, update_opportunity_history


class OpportunityTrendTests(unittest.TestCase):
    def test_applies_7_and_30_day_score_and_rank_deltas(self) -> None:
        opportunities = [
            {"query": "ai agent", "rank": 2, "score": 64.9},
        ]
        history = [
            {"snapshot_date": "2026-05-19", "query": "ai agent", "rank": "4", "score": "60.0"},
            {"snapshot_date": "2026-04-26", "query": "ai agent", "rank": "5", "score": "55.0"},
        ]

        apply_opportunity_trends(opportunities, history, "2026-05-26")

        result = opportunities[0]
        self.assertEqual(result["comparison_date_7d"], "2026-05-19")
        self.assertEqual(result["score_delta_7d"], 4.9)
        self.assertEqual(result["rank_delta_7d"], 2)
        self.assertEqual(result["comparison_date_30d"], "2026-04-26")
        self.assertEqual(result["score_delta_30d"], 9.9)
        self.assertEqual(result["rank_delta_30d"], 3)
        self.assertEqual(result["trend_status"], "rising")

    def test_update_history_replaces_same_day_query_snapshot(self) -> None:
        history = [
            {"snapshot_date": "2026-05-26", "query": "ai agent", "rank": "3", "score": "61.0"},
            {"snapshot_date": "2026-05-19", "query": "ai agent", "rank": "4", "score": "60.0"},
        ]
        opportunities = [
            {
                "query": "ai agent",
                "rank": 1,
                "score": 64.9,
                "grade": "C",
                "buyer_intent": 0.5,
                "pain_signal": 0.4,
                "commercial_relevance": 0.7,
                "market_size_growth": 0.6,
                "competition_attractiveness": 0.9,
                "execution_feasibility": 0.8,
                "commercial_gap": 0.7,
                "confidence": 0.8,
                "counts": {"github": 100, "producthunt": 5},
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opportunity_history.csv"
            update_opportunity_history(path, history, opportunities, "2026-05-26")

            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 2)
        current = [row for row in rows if row["snapshot_date"] == "2026-05-26"][0]
        self.assertEqual(current["rank"], "1")
        self.assertEqual(current["score"], "64.9")
        self.assertEqual(current["result_total"], "105")


if __name__ == "__main__":
    unittest.main()
