"""Command line interface for compliance assessments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import load_model_adapter
from .data import load_dataset_adapter
from .evaluation import ComplianceEvaluator
from .operations import compare_assessments, load_assessment_json
from .reporting import export_assessment_json, export_assessment_markdown, export_assessment_pdf


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a compliance assessment over a compatible model and dataset.")
    parser.add_argument("--framework", choices=["keras", "tensorflow", "pytorch"], required=True)
    parser.add_argument("--model-path", type=Path, required=True, help="Path to the serialized model artifact.")
    parser.add_argument("--input", type=Path, required=True, help="Path to a dataset file (json or csv).")
    parser.add_argument("--dataset-format", choices=["auto", "json", "csv"], default="auto")
    parser.add_argument("--features-key", type=str, default="features")
    parser.add_argument("--labels-key", type=str, default="labels")
    parser.add_argument("--metadata-key", type=str, default="metadata")
    parser.add_argument("--feature-columns", nargs="+", default=None)
    parser.add_argument("--label-column", type=str, default=None)
    parser.add_argument("--metadata-columns", nargs="+", default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--stress-domain", type=str, default=None, help="Stress taxonomy domain to use for robustness tests.")
    parser.add_argument(
        "--stress-taxonomy-config",
        type=Path,
        default=None,
        help="Optional TOML file for domain stress taxonomies (defaults to ./stress_taxonomies.toml if present).",
    )
    parser.add_argument("--model-name", type=str, default=None, help="Optional display name for the loaded model.")
    parser.add_argument("--run-id", type=str, default=None, help="Optional explicit run identifier.")
    parser.add_argument(
        "--previous-assessment-json",
        type=Path,
        default=None,
        help="Optional previous assessment JSON used to compute run-to-run deltas.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dataset = load_dataset_adapter(
        args.input,
        dataset_format=args.dataset_format,
        features_key=args.features_key,
        labels_key=args.labels_key,
        metadata_key=args.metadata_key,
        feature_columns=args.feature_columns,
        label_column=args.label_column,
        metadata_columns=args.metadata_columns,
    )
    model = load_model_adapter(args.framework, args.model_path, model_name=args.model_name)

    evaluator = ComplianceEvaluator(
        prediction_threshold=args.threshold,
        batch_size=args.batch_size,
        stress_domain=args.stress_domain,
        stress_taxonomy_path=args.stress_taxonomy_config,
    )
    assessment, summary = evaluator.evaluate(model, dataset)

    if args.run_id:
        assessment.run_id = args.run_id
        summary.run_id = args.run_id

    if args.previous_assessment_json and args.previous_assessment_json.exists():
        previous_assessment = load_assessment_json(args.previous_assessment_json)
        assessment.comparison_to_previous_run = compare_assessments(assessment.to_dict(), previous_assessment)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = export_assessment_json(assessment, args.output_dir / "assessment.json")
    md_path = export_assessment_markdown(assessment, args.output_dir / "assessment.md")
    pdf_path = export_assessment_pdf(assessment, args.output_dir / "assessment.pdf")

    print(
        json.dumps(
            {
                "json_report": str(json_path),
                "markdown_report": str(md_path),
                "pdf_report": str(pdf_path),
                "sample_count": summary.sample_count,
                "batch_count": summary.batch_count,
                "model_name": summary.model_name,
                "framework": summary.framework,
                "stress_domain": summary.stress_domain,
                "run_id": summary.run_id,
                "config_hash": summary.config_hash,
                "comparison_available": assessment.comparison_to_previous_run is not None,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())