#!/usr/bin/env python3
"""CLI entry point for risk and FMEA enrichment."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from eu_ai_act.compliance.fmea import FMEAConfig, FMEAEnricher, FMEAScore
from eu_ai_act.compliance.risk import RiskConfig, RiskEnricher, RiskRecord, RiskRegister

load_dotenv()


def load_assessment(input_path: Path) -> dict:
    """Load assessment JSON file."""
    with open(input_path) as f:
        return json.load(f)


def create_fmea_scores_from_dict(scores_data: list[dict]) -> list[FMEAScore]:
    """Create FMEAScore objects from dictionary data."""
    scores = []
    for score_data in scores_data:
        scores.append(FMEAScore(
            severity=score_data.get("severity", 5),
            occurrence=score_data.get("occurrence", 3),
            detectability=score_data.get("detectability", 3),
            failure_mode=score_data.get("failure_mode"),
            root_cause_category=score_data.get("root_cause_category"),
            root_cause=score_data.get("root_cause"),
            current_controls=score_data.get("current_controls"),
            recommended_actions=score_data.get("recommended_actions"),
            mitigation_strategy=score_data.get("mitigation_strategy"),
            monitoring_recommendations=score_data.get("monitoring_recommendations"),
            evidence_from_data=score_data.get("evidence_from_data"),
            residual_rpn=score_data.get("residual_rpn"),
            action_required=score_data.get("action_required", False),
            action_priority=score_data.get("action_priority"),
            insights_source=score_data.get("insights_source", "rule_based"),
        ))
    return scores


def create_risk_register_from_dict(register_data: dict) -> RiskRegister:
    """Create RiskRegister from dictionary data."""
    register = RiskRegister()
    records_data = register_data.get("records", [])

    for record_data in records_data:
        record = RiskRecord(
            risk_id=record_data.get("risk_id", ""),
            title=record_data.get("title", ""),
            description=record_data.get("description", ""),
            severity=record_data.get("severity", 5),
            occurrence=record_data.get("occurrence", 3),
            detectability=record_data.get("detectability", 3),
            strategy=record_data.get("strategy", "mitigate"),
            cause=record_data.get("cause"),
            current_controls=record_data.get("current_controls"),
            recommended_action=record_data.get("recommended_action"),
            residual_rpn=record_data.get("residual_rpn"),
        )
        register.add(record)

    return register


async def enrich_assessment_async(
    assessment: dict,
    domain: str | None = None,
    config_path: Path | None = None,
    model_id: str = "deepseek-v4-flash",
    api_key: str | None = None,
    base_url: str = "https://opencode.ai/zen/go/v1",
) -> dict:
    """Enrich assessment with AI-powered FMEA analysis using full assessment context."""
    enriched = assessment.copy()

    fmea_config = FMEAConfig(config_path=config_path, domain=domain)
    risk_config = RiskConfig(config_path=config_path, domain=domain)

    if "fmea_scores" in assessment:
        fmea_enricher = FMEAEnricher(
            fmea_config,
            use_ai=True,
            model_id=model_id,
            api_key=api_key,
            base_url=base_url
        )
        scores = create_fmea_scores_from_dict(assessment["fmea_scores"])
        enriched_scores = await fmea_enricher.enrich_scores_with_ai(scores, assessment)
        enriched["fmea_scores"] = [score.to_dict() for score in enriched_scores]

    if "risk_register" in assessment:
        risk_enricher = RiskEnricher(risk_config)
        register = create_risk_register_from_dict(assessment["risk_register"])
        enriched_register = risk_enricher.enrich_register(register)
        enriched["risk_register"] = enriched_register.to_dict()

    return enriched


def enrich_assessment(
    assessment: dict,
    domain: str | None = None,
    config_path: Path | None = None,
    model_id: str = "deepseek-v4-flash",
    api_key: str | None = None,
    base_url: str = "https://opencode.ai/zen/go/v1",
) -> dict:
    """Enrich assessment with AI-powered FMEA analysis using full assessment context."""
    return asyncio.run(enrich_assessment_async(
        assessment,
        domain=domain,
        config_path=config_path,
        model_id=model_id,
        api_key=api_key,
        base_url=base_url,
    ))


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the enrichment script."""
    parser = argparse.ArgumentParser(
        description="Enrich risk and FMEA analysis with AI-powered insights using full assessment context."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to input assessment JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to output enriched assessment JSON file.",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default=None,
        help="Domain for domain-specific enrichment (e.g., radiology, autonomous_vehicles).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to custom risk configuration TOML file.",
    )
    parser.add_argument(
        "--model-id",
        type=str,
        default="deepseek-v4-flash",
        help="AI model ID for insights generation (default: deepseek-v4-flash).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for the AI model. Can also be set via ZEN_API_KEY environment variable.",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="https://opencode.ai/zen/go/v1",
        help="Base URL for the AI API (default: https://opencode.ai/zen/go/v1).",
    )

    args = parser.parse_args(argv)

    try:
        assessment = load_assessment(args.input)
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        return 1

    api_key = args.api_key or os.environ.get("ZEN_API_KEY")

    print(f"Enriching assessment with AI (model: {args.model_id})...")
    enriched = enrich_assessment(
        assessment,
        domain=args.domain,
        config_path=args.config,
        model_id=args.model_id,
        api_key=api_key,
        base_url=args.base_url,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)

    print(f"Enriched assessment saved to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())