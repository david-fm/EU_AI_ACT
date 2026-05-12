#!/usr/bin/env python3
"""Export assessment results to PDF/MD/JSON formats.

This script unifies the reporting pipeline for both baseline assessments
(from Module 0) and enriched assessments (from Module 1).

Usage:
    # Export all formats
    python scripts/export_report.py --input assessment.json --output-dir ./reports

    # Specific format
    python scripts/export_report.py --input assessment_enriched.json --format pdf --output report.pdf
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def load_assessment(path: Path) -> dict:
    """Load assessment dictionary from JSON file."""
    with open(path) as f:
        return json.load(f)


def _is_enriched(report: dict[str, Any]) -> bool:
    """Check if assessment has enriched FMEA data."""
    fmea_scores = report.get("fmea_scores", [])
    if not fmea_scores:
        return False
    first_score = fmea_scores[0] if isinstance(fmea_scores[0], dict) else {}
    return "action_priority" in first_score or "root_cause" in first_score


def _has_ai_insights(report: dict[str, Any]) -> bool:
    """Check if assessment has AI-generated insights."""
    fmea_scores = report.get("fmea_scores", [])
    if not fmea_scores:
        return False
    return any(s.get("insights_source") == "ai" for s in fmea_scores if isinstance(s, dict))


def export_json(data: dict, output_path: Path) -> Path:
    """Export assessment to JSON format."""
    path = Path(output_path)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def export_markdown(data: dict, output_path: Path) -> Path:
    """Export assessment to Markdown format."""
    path = Path(output_path)
    is_enriched = _is_enriched(data)

    lines = [
        f"# Compliance Assessment: {data['model_name']}",
        f"- Framework: {data['framework']}",
        f"- Run ID: {data.get('run_metadata', {}).get('run_id')}",
        f"- Config hash: {data.get('run_metadata', {}).get('config_hash')}",
        f"- Run timestamp (UTC): {data.get('run_metadata', {}).get('run_timestamp_utc')}",
        f"- Stress domain: {data.get('stress_domain', 'generic')}",
        f"- Risk records: {data['risk_register']['total_records']}",
        f"- Report type: {'Enriched FMEA' if is_enriched else 'Baseline'}",
        "",
    ]

    lines.append("## 1. Risk Register (Art. 9.2)")
    for record in data["risk_register"]["records"]:
        lines.append(f"### {record.get('risk_id', 'N/A')}: {record.get('title', 'Untitled risk')}")
        lines.extend([
            f"- Severity: {record.get('severity', 'N/A')}",
            f"- Occurrence: {record.get('occurrence', 'N/A')}",
            f"- Detectability: {record.get('detectability', 'N/A')}",
            f"- RPN: {record.get('rpn', 'N/A')}",
            f"- Strategy: {record.get('strategy', 'N/A')}",
        ])
        if is_enriched:
            if "mitigation_status" in record:
                lines.append(f"- Mitigation status: {record['mitigation_status']}")
            if record.get("residual_rpn") is not None:
                lines.append(f"- Residual RPN: {record['residual_rpn']}")
            if record.get("current_controls"):
                lines.append(f"- Current controls: {record['current_controls']}")
            if record.get("recommended_action"):
                lines.append(f"- Recommended action: {record['recommended_action']}")
        lines.append("")

    if is_enriched:
        lines.append("## 2. FMEA Analysis")
        for i, score in enumerate(data.get("fmea_scores", []), 1):
            lines.append(f"### FMEA #{i}")
            insights_source = score.get("insights_source", "rule_based")
            source_badge = " [AI]" if insights_source == "ai" else " [Rule]"
            lines.extend([
                f"- Failure Mode: {score.get('failure_mode', 'N/A')}{source_badge}",
                f"- S: {score.get('severity', 'N/A')} | O: {score.get('occurrence', 'N/A')} | D: {score.get('detectability', 'N/A')} → RPN: {score.get('rpn', 'N/A')}",
                f"- Action Priority: {score.get('action_priority', 'N/A')}",
                f"- Action Required: {'Yes' if score.get('action_required') else 'No'}",
            ])
            if score.get("root_cause_category"):
                lines.append(f"- Root Cause Category: {score['root_cause_category']}")
            if score.get("root_cause"):
                lines.append(f"- Root Cause Analysis: {score['root_cause']}")
            if score.get("recommended_actions"):
                lines.append(f"- Recommended Actions: {score['recommended_actions']}")
            if score.get("mitigation_strategy"):
                lines.append(f"- Mitigation Strategy: {score['mitigation_strategy']}")
            if score.get("monitoring_recommendations"):
                lines.append(f"- Monitoring Recommendations: {score['monitoring_recommendations']}")
            if score.get("evidence_from_data"):
                lines.append(f"- Evidence from Data: {', '.join(score['evidence_from_data'])}")
            if score.get("residual_rpn") is not None:
                lines.append(f"- Residual RPN: {score['residual_rpn']}")
            lines.append("")

    comparison = data.get("comparison_to_previous_run")
    if comparison:
        lines.append("## Run Comparison")
        for key, value in comparison.items():
            lines.append(f"- {key}: {value}")
        lines.append("")

    if data.get("stress_results"):
        lines.append("## Stress Testing")
        for result in data["stress_results"]:
            lines.append(f"### {result['perturbation_name']} ({result['perturbation_kind']})")
            lines.extend([
                f"- Drop: {result['performance_drop']:.4f} | Max: {result.get('max_performance_drop', result['performance_drop']):.4f}",
                f"- Entropy: {result['average_entropy']:.4f}",
            ])

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _wrap_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = word
        else:
            lines.append(word[:max_chars])
            current = word[max_chars:]
    if current:
        lines.append(current)
    return lines


def export_pdf(data: dict, output_path: Path) -> Path:
    """Export assessment to styled PDF format."""
    path = Path(output_path)
    is_enriched = _is_enriched(data)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("AuditTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=colors.HexColor("#1a3a52"), alignment=TA_LEFT, spaceAfter=3 * mm)
    subtitle_style = ParagraphStyle("AuditSubtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#4b5d6b"), spaceAfter=5 * mm)
    section_style = ParagraphStyle("SectionHeader", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=13, textColor=colors.HexColor("#2c3e50"), spaceBefore=4 * mm, spaceAfter=2 * mm)
    label_style = ParagraphStyle("Label", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor("#6c757d"))
    value_style = ParagraphStyle("Value", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=colors.HexColor("#2c3e50"))
    card_title_style = ParagraphStyle("CardTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=colors.HexColor("#212529"))
    card_text_style = ParagraphStyle("CardText", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor("#495057"))
    centered_footer_style = ParagraphStyle("CenteredFooter", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10, textColor=colors.white, alignment=TA_CENTER)
    priority_high_style = ParagraphStyle("PriorityHigh", parent=card_text_style, textColor=colors.HexColor("#c0392b"), fontName="Helvetica-Bold")
    priority_medium_style = ParagraphStyle("PriorityMedium", parent=card_text_style, textColor=colors.HexColor("#d35400"))
    priority_low_style = ParagraphStyle("PriorityLow", parent=card_text_style, textColor=colors.HexColor("#27ae60"))

    story = []

    story.append(Paragraph("EU AI ACT - COMPLIANCE AUDIT REPORT", title_style))
    story.append(Paragraph(f"Assessment report {'(Enriched)' if is_enriched else ''} | EU AI Act Article 9", subtitle_style))

    metadata = [
        [Paragraph("Model", label_style), Paragraph("Framework", label_style)],
        [Paragraph(str(data.get("model_name", "N/A")), value_style), Paragraph(str(data.get("framework", "N/A")), value_style)],
        [Paragraph("Run ID", label_style), Paragraph("Timestamp (UTC)", label_style)],
        [Paragraph(str(data.get("run_metadata", {}).get("run_id", "N/A")), value_style), Paragraph(str(data.get("run_metadata", {}).get("run_timestamp_utc", "N/A")), value_style)],
    ]
    metadata_table = Table(metadata, colWidths=[doc.width / 2, doc.width / 2])
    metadata_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef3f6")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cfd8df")), ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9e1e7")), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(metadata_table)
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("1. Risk Register (Art. 9.2)", section_style))
    risk_records = data.get("risk_register", {}).get("records", [])
    if not risk_records:
        story.append(Paragraph("No risk records available.", card_text_style))
    for record in risk_records:
        is_high_risk = bool(record.get("high_risk", False))
        risk_color = colors.HexColor("#e74c3c") if is_high_risk else colors.HexColor("#27ae60")
        risk_status = "HIGH RISK" if is_high_risk else "Mitigated"

        risk_header = Table([[Paragraph(f"{record.get('risk_id', 'N/A')} - {record.get('title', 'Untitled risk')}", card_title_style), Paragraph(risk_status, ParagraphStyle("RiskStatus", parent=card_title_style, textColor=risk_color, alignment=TA_CENTER))]], colWidths=[doc.width * 0.78, doc.width * 0.22])
        risk_header.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7f9fb")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9e1e7")), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("VALIGN", (0, 0), (-1, -1), "TOP")]))

        if is_enriched:
            detail_rows = [[Paragraph(f"RPN: {record.get('rpn', 'N/A')} (S:{record.get('severity', 'N/A')}, O:{record.get('occurrence', 'N/A')}, D:{record.get('detectability', 'N/A')})", card_text_style), Paragraph(f"Strategy: {str(record.get('strategy', 'N/A')).upper()}", card_text_style)]]
            if "mitigation_status" in record:
                detail_rows.append([Paragraph(f"Mitigation: {record['mitigation_status']}", card_text_style), Paragraph(f"Residual RPN: {record.get('residual_rpn', 'N/A')}", card_text_style)])
            if record.get("current_controls"):
                ctrl = record["current_controls"]
                if len(ctrl) > 60:
                    ctrl = ctrl[:60] + "..."
                detail_rows.append([Paragraph(f"Controls: {ctrl}", card_text_style), Paragraph("", card_text_style)])
            risk_detail = Table(detail_rows, colWidths=[doc.width * 0.5, doc.width * 0.5])
        else:
            risk_detail = Table([[Paragraph(f"RPN: {record.get('rpn', 'N/A')} (S:{record.get('severity', 'N/A')}, O:{record.get('occurrence', 'N/A')}, D:{record.get('detectability', 'N/A')})", card_text_style), Paragraph(f"Strategy: {str(record.get('strategy', 'N/A')).upper()}", card_text_style)], [Paragraph(f"Cause: {record.get('cause', 'N/A')}", card_text_style), Paragraph(f"Action: {record.get('recommended_action', 'N/A')}", card_text_style)]], colWidths=[doc.width * 0.5, doc.width * 0.5])

        risk_detail.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.white), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9e1e7")), ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#edf1f4")), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(KeepTogether([risk_header, risk_detail, Spacer(1, 2.5 * mm)]))

    if is_enriched:
        story.append(Paragraph("2. FMEA Analysis", section_style))
        has_ai = _has_ai_insights(data)
        if has_ai:
            ai_badge_style = ParagraphStyle("AIBadge", parent=card_text_style, textColor=colors.HexColor("#6c5ce7"), fontName="Helvetica-Bold")
            story.append(Paragraph("[AI-Powered Analysis] This section contains AI-generated insights based on actual assessment data.", ai_badge_style))
            story.append(Spacer(1, 2 * mm))

        for score in data.get("fmea_scores", []):
            rpn = score.get("rpn", 0)
            priority = score.get("action_priority", "none")
            insights_source = score.get("insights_source", "rule_based")

            if priority == "high":
                priority_style = priority_high_style
                priority_label = "HIGH"
            elif priority == "medium":
                priority_style = priority_medium_style
                priority_label = "MEDIUM"
            elif priority == "low":
                priority_style = priority_low_style
                priority_label = "LOW"
            else:
                priority_style = card_text_style
                priority_label = "NONE"

            source_tag = "[AI]" if insights_source == "ai" else "[Rule]"
            fmea_header = Table([[Paragraph(f"Failure: {score.get('failure_mode', 'Unknown')}", card_title_style), Paragraph(f"{priority_label} {source_tag}", ParagraphStyle("PriorityIndicator", parent=priority_style, alignment=TA_CENTER))]], colWidths=[doc.width * 0.65, doc.width * 0.35])
            fmea_header.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f7ff")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#a3c4e8")), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("VALIGN", (0, 0), (-1, -1), "TOP")]))

            fmea_rpn_row = Table([[Paragraph(f"RPN: {rpn} | S:{score.get('severity', 'N/A')} × O:{score.get('occurrence', 'N/A')} × D:{score.get('detectability', 'N/A')}", card_text_style), Paragraph(f"Action Required: {'Yes' if score.get('action_required') else 'No'}", card_text_style)]], colWidths=[doc.width * 0.65, doc.width * 0.35])
            fmea_rpn_row.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.white), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0dae2")), ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5ebf0")), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("VALIGN", (0, 0), (-1, -1), "TOP")]))

            detail_rows = []
            if score.get("root_cause_category"):
                detail_rows.append([Paragraph("Category:", label_style), Paragraph(score["root_cause_category"], card_text_style)])
            if score.get("root_cause"):
                detail_rows.append([Paragraph("Root Cause:", label_style), Paragraph(score["root_cause"], card_text_style)])
            if score.get("recommended_actions"):
                actions = score["recommended_actions"]
                if isinstance(actions, str):
                    actions = actions.split(";")
                actions_text = "; ".join(actions[:3])
                detail_rows.append([Paragraph("Actions:", label_style), Paragraph(actions_text, card_text_style)])
            if score.get("mitigation_strategy"):
                detail_rows.append([Paragraph("Mitigation:", label_style), Paragraph(score["mitigation_strategy"], card_text_style)])
            if score.get("monitoring_recommendations"):
                mr = score["monitoring_recommendations"]
                if isinstance(mr, str):
                    mr = mr.split(";")
                mr_text = "; ".join(mr[:2])
                detail_rows.append([Paragraph("Monitoring:", label_style), Paragraph(mr_text, card_text_style)])
            if score.get("evidence_from_data"):
                ev = ", ".join(score["evidence_from_data"][:3])
                detail_rows.append([Paragraph("Evidence:", label_style), Paragraph(ev, ParagraphStyle("Evidence", parent=card_text_style, textColor=colors.HexColor("#6c5ce7")))])
            if score.get("residual_rpn") is not None:
                detail_rows.append([Paragraph("Residual RPN:", label_style), Paragraph(str(score["residual_rpn"]), card_text_style)])

            if detail_rows:
                fmea_detail = Table(detail_rows, colWidths=[doc.width * 0.2, doc.width * 0.8])
                fmea_detail.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.white), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0dae2")), ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5ebf0")), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
                story.append(fmea_header)
                story.append(fmea_rpn_row)
                story.append(fmea_detail)
                story.append(Spacer(1, 3 * mm))

    section_num = "2" if is_enriched else "2"
    story.append(Paragraph(f"{section_num}. Robustness and Stress Testing", section_style))
    stress_results = data.get("stress_results", [])
    if stress_results:
        stress_rows = [[Paragraph("Case", label_style), Paragraph("Kind", label_style), Paragraph("Drop", label_style), Paragraph("Severity", label_style), Paragraph("Entropy", label_style)]]
        for result in stress_results:
            stress_rows.append([Paragraph(str(result.get("perturbation_name", "N/A")), card_text_style), Paragraph(str(result.get("perturbation_kind", "N/A")), card_text_style), Paragraph(f"{float(result.get('performance_drop', 0.0)):.3f}", card_text_style), Paragraph(f"{float(result.get('severity', 0.0)):.2f}", card_text_style), Paragraph(f"{float(result.get('average_entropy', 0.0)):.3f}", card_text_style)])
        stress_table = Table(stress_rows, colWidths=[doc.width * 0.32, doc.width * 0.15, doc.width * 0.14, doc.width * 0.14, doc.width * 0.25], repeatRows=1)
        stress_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecf2f7")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2c3e50")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0dae2")), ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5ebf0")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        story.append(stress_table)
    else:
        story.append(Paragraph("No stress testing results available.", card_text_style))

    story.append(Spacer(1, 2.5 * mm))
    section_num = "3" if is_enriched else "3"
    story.append(Paragraph(f"{section_num}. Fairness and Bias Assessment (Art. 9.9)", section_style))
    fairness_results = data.get("fairness_results", [])
    fairness_critical = [item for item in fairness_results if "disparate_impact" in item.get("metric_name", "") or "equalized_odds_gap" in item.get("metric_name", "")][:8]
    if fairness_critical:
        fairness_rows = [[Paragraph("Metric", label_style), Paragraph("Values", label_style)]]
        for item in fairness_critical:
            metric_name = item.get("metric_name", "metric").replace("_", " ").title()
            group_text = ", ".join(f"{group.get('group_name', 'group')}={float(group.get('value', 0.0)):.4f}" for group in item.get("groups", [])[:4])
            fairness_rows.append([Paragraph(metric_name, card_text_style), Paragraph(group_text if group_text else "N/A", card_text_style)])
        fairness_table = Table(fairness_rows, colWidths=[doc.width * 0.44, doc.width * 0.56], repeatRows=1)
        fairness_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecf2f7")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0dae2")), ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5ebf0")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        story.append(fairness_table)
    else:
        story.append(Paragraph("No fairness metrics available.", card_text_style))

    story.append(Spacer(1, 2.5 * mm))
    section_num = "4" if is_enriched else "4"
    story.append(Paragraph(f"{section_num}. Transparency Card (Art. 13)", section_style))
    transparency_rows = [[Paragraph("Intended use", label_style), Paragraph("Declared by deployer in system setup", card_text_style)], [Paragraph("Known constraints", label_style), Paragraph("See fairness and robustness sections above", card_text_style)], [Paragraph("Recommended mitigations", label_style), Paragraph("See risk register strategies and action items", card_text_style)]]
    transparency_table = Table(transparency_rows, colWidths=[doc.width * 0.26, doc.width * 0.74])
    transparency_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0dae2")), ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5ebf0")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(transparency_table)

    story.append(Spacer(1, 4 * mm))
    total_risks = data.get("risk_register", {}).get("total_records", 0)
    fmea_count = len(data.get("fmea_scores", [])) if is_enriched else 0
    end_label = f"End of Report | Risks: {total_risks}" + (f" | FMEA Items: {fmea_count}" if is_enriched else "")
    end_bar = Table([[Paragraph(end_label, centered_footer_style)]], colWidths=[doc.width])
    end_bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#34495e")), ("BOX", (0, 0), (-1, -1), 0, colors.HexColor("#34495e")), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(end_bar)

    def _draw_page_footer(pdf_canvas, pdf_doc):
        pdf_canvas.saveState()
        pdf_canvas.setFont("Helvetica", 8)
        pdf_canvas.setFillColor(colors.HexColor("#7f8c8d"))
        pdf_canvas.drawRightString(pdf_doc.pagesize[0] - doc.rightMargin, 8 * mm, f"Page {pdf_doc.page}")
        pdf_canvas.restoreState()

    doc.build(story, onFirstPage=_draw_page_footer, onLaterPages=_draw_page_footer)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export assessment results to PDF/MD/JSON formats. Unifies baseline and enriched assessments.")
    parser.add_argument("--input", type=Path, required=True, help="Path to assessment JSON file (baseline or enriched).")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory for generated files.")
    parser.add_argument("--output", type=Path, default=None, help="Output file path (use with --format for single output).")
    parser.add_argument("--format", choices=["pdf", "md", "json", "all"], default="all", help="Output format (default: all).")
    parser.add_argument("--base-name", type=str, default=None, help="Base name for output files (without extension).")

    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=__import__("sys").stderr)
        return 1

    data = load_assessment(args.input)
    is_enriched = _is_enriched(data)

    if args.base_name:
        base_name = args.base_name
    else:
        base_name = args.input.stem

    if args.output:
        if args.format == "pdf":
            path = export_pdf(data, args.output)
        elif args.format == "md":
            path = export_markdown(data, args.output)
        else:
            path = export_json(data, args.output)
        print(f"Exported to: {path}")
        return 0

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
    else:
        args.output_dir = args.input.parent

    formats = ["pdf", "md", "json"] if args.format == "all" else [args.format]
    results = {}

    for fmt in formats:
        output_path = args.output_dir / f"{base_name}.{fmt}"
        if fmt == "pdf":
            export_pdf(data, output_path)
        elif fmt == "md":
            export_markdown(data, output_path)
        else:
            export_json(data, output_path)
        results[fmt] = output_path

    print(f"Assessment type: {'Enriched' if is_enriched else 'Baseline'}")
    print("Exported files:")
    for fmt, path in results.items():
        print(f"  - {fmt.upper()}: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())