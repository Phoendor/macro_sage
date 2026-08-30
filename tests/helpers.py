from __future__ import annotations

REGIME_DIMENSIONS = [
    "growth",
    "inflation",
    "monetary_policy",
    "fiscal_policy",
    "liquidity_financial_conditions",
    "risk_sentiment",
]


def claim(source_id: str, text: str = "Evidence supports the assessment.") -> dict:
    return {
        "text": text,
        "claim_type": "observed_fact",
        "source_ids": [source_id],
        "evidence_family": "fixture-release",
        "carried_forward": False,
    }


def v2_draft(source_id: str = "S001", *, expression: bool = False) -> dict:
    value = {
        "what_changed": [
            {
                "headline": "Policy signal changed",
                "significance": "The expected path is less certain.",
                "affected_assets": ["EUR/USD"],
                "transmission": "Rate differentials can affect the currency.",
                "horizon": "short_term",
                "source_ids": [source_id],
            }
        ],
        "executive_decisions": [
            {
                "rank": 1,
                "development": "Policy signal changed",
                "why_it_matters": "The expected rate path is less certain.",
                "transmission": "Rates can transmit into FX.",
                "urgency": "watch",
                "horizon": "short_term",
                "source_ids": [source_id],
            }
        ],
        "regime_dashboard": [
            {
                "dimension": dimension,
                "state": "mixed",
                "direction": "unclear",
                "horizon": "short_term",
                "confidence": 4,
                "confidence_rationale": "Fixture rationale.",
                "evidence": [claim(source_id)],
                "counterevidence": [],
                "source_ids": [source_id],
            }
            for dimension in REGIME_DIMENSIONS
        ],
        "macro_themes": [
            {
                "theme": "Policy uncertainty",
                "thesis": "Policy uncertainty remains elevated.",
                "market_implication": "Rate volatility may remain elevated.",
                "observed_facts": [claim(source_id)],
                "inferences": [
                    {
                        **claim(source_id, "Macro Sage infers wider outcome dispersion."),
                        "claim_type": "synthesis_inference",
                    }
                ],
                "conflicting_evidence": [],
                "unresolved_questions": ["Will the next release confirm the signal?"],
                "transmission": [
                    {"asset_class": "rates", "implication": "Volatility may stay high."},
                    {"asset_class": "fx", "implication": "Differentials may move."},
                ],
                "horizon": "short_term",
                "catalysts": ["Next sourced policy communication"],
                "invalidation_conditions": ["A clear reversal in the policy signal"],
                "source_ids": [source_id],
            }
        ],
        "asset_views": [
            {
                "asset": "EUR/USD",
                "bias": "mixed",
                "horizon": "short_term",
                "confidence": 4,
                "confidence_rationale": "Fixture rationale.",
                "market_confirmation": "unavailable",
                "thesis": "Policy uncertainty argues against a strong directional view.",
                "transmission": "Rate differentials remain the main channel.",
                "drivers": ["Policy uncertainty"],
                "risks": ["A decisive policy shift"],
                "catalyst": "Next sourced policy communication",
                "invalidation_condition": "Clear directional policy divergence",
                "evidence": [claim(source_id)],
                "counterevidence": [],
                "source_ids": [source_id],
            }
        ],
        "candidate_expressions": [],
        "scenarios": [
            {
                "kind": kind,
                "qualitative_likelihood": likelihood,
                "description": f"{kind.title()} scenario.",
                "signposts": ["A sourced policy signal"],
                "cross_asset_consequences": [
                    {"asset_class": "rates", "implication": "Yields respond."}
                ],
                "assumptions": [claim(source_id)],
                "source_ids": [source_id],
            }
            for kind, likelihood in (
                ("base", "leading"),
                ("upside", "plausible"),
                ("downside", "tail"),
            )
        ],
        "disagreements": [],
        "catalysts": [
            {
                "event_or_signpost": "Next policy communication",
                "timing": "date not supplied",
                "what_matters": "Whether the policy signal persists.",
                "affected_views": ["EUR/USD"],
                "source_ids": [source_id],
            }
        ],
        "top_risks": [
            {
                "risk": "Evidence is narrow",
                "why_it_matters": "One evidence family may not be representative.",
                "monitor": "Independent confirmation",
                "source_ids": [source_id],
            }
        ],
    }
    if expression:
        value["candidate_expressions"] = [
            {
                "thesis": "Policy divergence may widen.",
                "expression": "Monitor EUR/USD downside",
                "framing": "directional",
                "why_now": "The policy signal changed.",
                "catalyst": "Next policy communication",
                "expected_path": "Wider rate differentials could weigh on EUR/USD.",
                "horizon": "short_term",
                "invalidation_condition": "Policy convergence",
                "countercase": "Growth data could dominate rates.",
                "implementation_risks": ["Current valuation is unavailable"],
                "alternative_expression": "Monitor a rates spread instead",
                "evidence_quality": "One institutional evidence family",
                "thesis_confidence": 4,
                "expression_confidence": 4,
                "confidence_rationale": "Fixture rationale.",
                "source_ids": [source_id],
                "market_data_required": True,
                "actionability": "conditional",
            }
        ]
    return value


def v2_brief(source_id: str = "doc:one", *, failed: int = 0) -> dict:
    return {
        "schema_version": "2",
        "as_of_date": "2026-07-27",
        "coverage": {
            "data_cutoff": "2026-07-28T00:00:00+02:00",
            "comparison_date": "2026-07-24",
            "documents_collected": 1,
            "sources_collected": 1,
            "sources_failed_or_partial": failed,
            "sources_without_items": 0,
            "important_missing_coverage": [],
            "market_data_available": False,
            "market_data_note": "No timestamped market data is integrated.",
        },
        "source_ids_used": [source_id],
        **v2_draft(source_id, expression=True),
    }
