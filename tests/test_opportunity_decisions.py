from __future__ import annotations

import unittest

from shopping_intel.opportunity import score_opportunities


def search_row(
    query: str,
    source: str,
    result_count: int,
    buyer: int,
    pain: int,
    commercial: int,
    confidence: int = 80,
) -> dict[str, object]:
    return {
        "query": query,
        "source": source,
        "observed_rows": 5,
        "result_count": result_count,
        "avg_relevance": 0.9,
        "buyer_intent_score": buyer,
        "pain_score": pain,
        "commercial_relevance": commercial,
        "source_confidence": confidence,
    }


class OpportunityDecisionTests(unittest.TestCase):
    def test_strong_commercial_and_pain_signals_are_prioritized_for_paid_validation(self) -> None:
        opportunities = score_opportunities(
            {
                "search_summary": [
                    search_row("ai invoice processing", "google_ads", 900, 92, 76, 94),
                    search_row("ai invoice processing", "g2", 80, 88, 82, 92),
                    search_row("ai invoice processing", "github_issues", 300, 74, 90, 86),
                    search_row("ai invoice processing", "ai_dev_jobs", 120, 90, 72, 92),
                    search_row("ai invoice processing", "producthunt", 8, 82, 65, 90),
                    search_row("ai invoice processing", "github", 600, 35, 22, 55),
                ]
            }
        )

        result = opportunities[0]
        self.assertEqual(result["decision_tier"], "优先付费验证")
        self.assertEqual(result["evidence_level"], "付费代理证据")
        self.assertGreaterEqual(result["decision_score"], 68)
        self.assertIn("付费落地页", result["validation_test"])

    def test_technical_heat_without_commercial_proof_requires_more_evidence(self) -> None:
        opportunities = score_opportunities(
            {
                "search_summary": [
                    search_row("ai widget", "github", 5000, 25, 20, 45),
                    search_row("ai widget", "hackernews", 200, 30, 35, 50),
                ]
            }
        )

        result = opportunities[0]
        self.assertIn(result["decision_tier"], {"补证据后验证", "继续观察"})
        self.assertNotEqual(result["decision_tier"], "优先付费验证")
        self.assertTrue(any("缺少关键词广告" in gap for gap in result["validation_gaps"]))


if __name__ == "__main__":
    unittest.main()
