"""Export compliance assessments into portable formats."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..compliance import ComplianceAssessment


def _is_enriched(report: dict[str, Any]) -> bool:
    """Check if assessment has enriched FMEA data."""
    fmea_scores = report.get("fmea_scores", [])
    if not fmea_scores:
        return False
    first_score = fmea_scores[0] if isinstance(fmea_scores[0], dict) else {}
    return "action_priority" in first_score or "root_cause" in first_score


def export_assessment_json(assessment: ComplianceAssessment, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.write_text(json.dumps(assessment.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def export_assessment_markdown(assessment: ComplianceAssessment, output_path: str | Path) -> Path:
    path = Path(output_path)
    report = assessment.to_dict()
    is_enriched = _is_enriched(report)

    lines = [
        f"# Compliance Assessment: {report['model_name']}",
        f"- Framework: {report['framework']}",
        f"- Run ID: {report.get('run_metadata', {}).get('run_id')}",
        f"- Config hash: {report.get('run_metadata', {}).get('config_hash')}",
        f"- Run timestamp (UTC): {report.get('run_metadata', {}).get('run_timestamp_utc')}",
        f"- Stress domain: {report.get('stress_domain', 'generic')}",
        f"- Risk records: {report['risk_register']['total_records']}",
        f"- Report type: {'Enriched FMEA' if is_enriched else 'Baseline'}",
        "",
    ]

    # Risk Register
    lines.append("## 1. Risk Register (Art. 9.2)")
    for record in report["risk_register"]["records"]:
        lines.append(f"### {record.get('risk_id', 'N/A')}: {record.get('title', 'Untitled risk')}")
        lines.extend(
            [
                f"- Severity: {record.get('severity', 'N/A')}",
                f"- Occurrence: {record.get('occurrence', 'N/A')}",
                f"- Detectability: {record.get('detectability', 'N/A')}",
                f"- RPN: {record.get('rpn', 'N/A')}",
                f"- Strategy: {record.get('strategy', 'N/A')}",
            ]
        )
        # Enriched fields
        if is_enriched:
            if "mitigation_status" in record:
                lines.append(f"- Mitigation status: {record['mitigation_status']}")
            if "residual_rpn" in record and record["residual_rpn"] is not None:
                lines.append(f"- Residual RPN: {record['residual_rpn']}")
            if "current_controls" in record and record["current_controls"]:
                lines.append(f"- Current controls: {record['current_controls']}")
            if "recommended_action" in record and record["recommended_action"]:
                lines.append(f"- Recommended action: {record['recommended_action']}")
        lines.append("")

    # FMEA Scores (Enriched section)
    if is_enriched:
        lines.append("## 2. FMEA Analysis")
        for i, score in enumerate(report.get("fmea_scores", []), 1):
            lines.append(f"### FMEA #{i}")
            lines.extend(
                [
                    f"- Failure Mode: {score.get('failure_mode', 'N/A')}",
                    f"- Severity: {score.get('severity', 'N/A')} | Occurrence: {score.get('occurrence', 'N/A')} | Detectability: {score.get('detectability', 'N/A')}",
                    f"- RPN: {score.get('rpn', 'N/A')}",
                    f"- Action Priority: {score.get('action_priority', 'N/A')}",
                    f"- Action Required: {'Yes' if score.get('action_required') else 'No'}",
                ]
            )
            if score.get("root_cause"):
                lines.append(f"- Root Cause: {score['root_cause']}")
            if score.get("current_controls"):
                lines.append(f"- Current Controls: {score['current_controls']}")
            if score.get("recommended_actions"):
                lines.append(f"- Recommended Actions: {score['recommended_actions']}")
            if score.get("residual_rpn") is not None:
                lines.append(f"- Residual RPN: {score['residual_rpn']}")
            lines.append("")

    # Run Comparison
    comparison = report.get("comparison_to_previous_run")
    if comparison:
        lines.append("## Run Comparison")
        for key, value in comparison.items():
            lines.append(f"- {key}: {value}")
        lines.append("")

    # Stress Testing
    if report.get("stress_results"):
        lines.append("## Stress Testing")
        for result in report["stress_results"]:
            lines.append(f"### {result['perturbation_name']} ({result['perturbation_kind']})")
            lines.extend(
                [
                    f"- Severity: {result['severity']}",
                    f"- Reference metric: {result['reference_metric']}",
                    f"- Baseline value: {result['baseline_value']}",
                    f"- Stressed value: {result['stressed_value']}",
                    f"- Performance drop: {result['performance_drop']}",
                    f"- Max performance drop: {result.get('max_performance_drop', result['performance_drop'])}",
                    f"- Drop slope: {result.get('drop_slope', 0.0)}",
                    f"- Mean absolute delta: {result['mean_absolute_delta']}",
                    f"- Average entropy: {result['average_entropy']}",
                ]
            )
            severity_points = result.get("severity_points", [])
            if severity_points:
                lines.append("- Severity curve:")
                for point in severity_points:
                    lines.extend(
                        [
                            f"  - Severity {point['severity']}: drop {point['performance_drop']}",
                            f"    - Baseline: {point['baseline_value']}",
                            f"    - Stressed: {point['stressed_value']}",
                        ]
                    )
            lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def export_assessment_pdf(assessment: ComplianceAssessment, output_path: str | Path) -> Path:
    """Export a styled PDF audit report with automatic pagination and non-overlapping blocks.
    
    Handles both baseline assessments (from Module 0) and enriched assessments (from Module 1).
    Enriched assessments include FMEA analysis section and enhanced risk register fields.
    """

    path = Path(output_path)
    report = assessment.to_dict()
    is_enriched = _is_enriched(report)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AuditTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        textColor=colors.HexColor("#1a3a52"),
        alignment=TA_LEFT,
        spaceAfter=3 * mm,
    )
    subtitle_style = ParagraphStyle(
        "AuditSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4b5d6b"),
        spaceAfter=5 * mm,
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=13,
        textColor=colors.HexColor("#2c3e50"),
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#6c757d"),
    )
    value_style = ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#2c3e50"),
    )
    card_title_style = ParagraphStyle(
        "CardTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#212529"),
    )
    card_text_style = ParagraphStyle(
        "CardText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#495057"),
    )
    centered_footer_style = ParagraphStyle(
        "CenteredFooter",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    priority_high_style = ParagraphStyle(
        "PriorityHigh",
        parent=card_text_style,
        textColor=colors.HexColor("#c0392b"),
        fontName="Helvetica-Bold",
    )
    priority_medium_style = ParagraphStyle(
        "PriorityMedium",
        parent=card_text_style,
        textColor=colors.HexColor("#d35400"),
    )
    priority_low_style = ParagraphStyle(
        "PriorityLow",
        parent=card_text_style,
        textColor=colors.HexColor("#27ae60"),
    )

    story: list[object] = []

    story.append(Paragraph("EU AI ACT - COMPLIANCE AUDIT REPORT", title_style))
    story.append(Paragraph(f"Assessment report {'(Enriched)' if is_enriched else ''} | EU AI Act Article 9", subtitle_style))

    metadata = [
        [
            Paragraph("Model", label_style),
            Paragraph("Framework", label_style),
        ],
        [
            Paragraph(str(report.get("model_name", "N/A")), value_style),
            Paragraph(str(report.get("framework", "N/A")), value_style),
        ],
        [
            Paragraph("Run ID", label_style),
            Paragraph("Timestamp (UTC)", label_style),
        ],
        [
            Paragraph(str(report.get("run_metadata", {}).get("run_id", "N/A")), value_style),
            Paragraph(str(report.get("run_metadata", {}).get("run_timestamp_utc", "N/A")), value_style),
        ],
    ]
    metadata_table = Table(metadata, colWidths=[doc.width / 2, doc.width / 2])
    metadata_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef3f6")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cfd8df")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9e1e7")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(metadata_table)
    story.append(Spacer(1, 5 * mm))

    # Risk Register
    section_num = "1" if not is_enriched else "1"
    story.append(Paragraph(f"{section_num}. Risk Register (Art. 9.2)", section_style))
    risk_records = report.get("risk_register", {}).get("records", [])
    if not risk_records:
        story.append(Paragraph("No risk records available.", card_text_style))
    for record in risk_records:
        is_high_risk = bool(record.get("high_risk", False))
        risk_color = colors.HexColor("#e74c3c") if is_high_risk else colors.HexColor("#27ae60")
        risk_status = "HIGH RISK" if is_high_risk else "Mitigated"

        risk_header = Table(
            [[
                Paragraph(f"{record.get('risk_id', 'N/A')} - {record.get('title', 'Untitled risk')}", card_title_style),
                Paragraph(risk_status, ParagraphStyle("RiskStatus", parent=card_title_style, textColor=risk_color, alignment=TA_CENTER)),
            ]],
            colWidths=[doc.width * 0.78, doc.width * 0.22],
        )
        risk_header.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7f9fb")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9e1e7")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        # Build detail rows based on enrichment status
        if is_enriched:
            # Enriched: show residual RPN, mitigation status, current controls, recommended action
            detail_rows = [
                [
                    Paragraph(
                        (
                            f"RPN: {record.get('rpn', 'N/A')} "
                            f"(S:{record.get('severity', 'N/A')}, "
                            f"O:{record.get('occurrence', 'N/A')}, "
                            f"D:{record.get('detectability', 'N/A')})"
                        ),
                        card_text_style,
                    ),
                    Paragraph(f"Strategy: {str(record.get('strategy', 'N/A')).upper()}", card_text_style),
                ],
            ]
            if "mitigation_status" in record:
                detail_rows.append([
                    Paragraph(f"Mitigation: {record['mitigation_status']}", card_text_style),
                    Paragraph(f"Residual RPN: {record.get('residual_rpn', 'N/A')}", card_text_style),
                ])
            if "current_controls" in record and record["current_controls"]:
                detail_rows.append([
                    Paragraph(f"Controls: {record['current_controls'][:60]}...", card_text_style),
                    Paragraph("", card_text_style),
                ])
            if "recommended_action" in record and record["recommended_action"]:
                detail_rows.append([
                    Paragraph(f"Action: {record['recommended_action'][:60]}...", card_text_style),
                    Paragraph("", card_text_style),
                ])
            risk_detail = Table(detail_rows, colWidths=[doc.width * 0.5, doc.width * 0.5])
        else:
            # Baseline: original fields
            risk_detail = Table(
                [
                    [
                        Paragraph(
                            (
                                f"RPN: {record.get('rpn', 'N/A')} "
                                f"(S:{record.get('severity', 'N/A')}, "
                                f"O:{record.get('occurrence', 'N/A')}, "
                                f"D:{record.get('detectability', 'N/A')})"
                            ),
                            card_text_style,
                        ),
                        Paragraph(f"Strategy: {str(record.get('strategy', 'N/A')).upper()}", card_text_style),
                    ],
                    [
                        Paragraph(f"Cause: {record.get('cause', 'N/A')}", card_text_style),
                        Paragraph(f"Action: {record.get('recommended_action', 'N/A')}", card_text_style),
                    ],
                ],
                colWidths=[doc.width * 0.5, doc.width * 0.5],
            )

        risk_detail.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9e1e7")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#edf1f4")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        story.append(KeepTogether([risk_header, risk_detail, Spacer(1, 2.5 * mm)]))

    # FMEA Scores Section (Enriched only)
    if is_enriched:
        story.append(Paragraph("2. FMEA Analysis", section_style))
        fmea_scores = report.get("fmea_scores", [])
        if not fmea_scores:
            story.append(Paragraph("No FMEA scores available.", card_text_style))
        else:
            for score in fmea_scores:
                rpn = score.get("rpn", 0)
                priority = score.get("action_priority", "none")
                action_required = score.get("action_required", False)

                # Determine priority styling
                if priority == "high":
                    priority_style = priority_high_style
                    priority_label = "HIGH PRIORITY"
                elif priority == "medium":
                    priority_style = priority_medium_style
                    priority_label = "MEDIUM"
                elif priority == "low":
                    priority_style = priority_low_style
                    priority_label = "LOW"
                else:
                    priority_style = card_text_style
                    priority_label = "NONE"

                fmea_header = Table(
                    [[
                        Paragraph(f"Failure: {score.get('failure_mode', 'Unknown')}", card_title_style),
                        Paragraph(priority_label, ParagraphStyle("PriorityIndicator", parent=priority_style, alignment=TA_CENTER)),
                    ]],
                    colWidths=[doc.width * 0.7, doc.width * 0.3],
                )
                fmea_header.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f7ff")),
                            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#a3c4e8")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ]
                    )
                )

                fmea_rpn_row = Table(
                    [[
                        Paragraph(
                            f"RPN: {rpn} | S:{score.get('severity', 'N/A')} × O:{score.get('occurrence', 'N/A')} × D:{score.get('detectability', 'N/A')}",
                            card_text_style
                        ),
                        Paragraph(f"Action Required: {'Yes' if action_required else 'No'}", card_text_style),
                    ]],
                    colWidths=[doc.width * 0.65, doc.width * 0.35],
                )
                fmea_rpn_row.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0dae2")),
                            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5ebf0")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ]
                    )
                )

                # Root cause and recommended actions
                detail_rows = []
                if score.get("root_cause"):
                    detail_rows.append([Paragraph("Root Cause:", label_style), Paragraph(_wrap_text(score["root_cause"], 80)[0] if len(_wrap_text(score["root_cause"], 80)) > 0 else score["root_cause"], card_text_style)])
                if score.get("recommended_actions"):
                    actions = score["recommended_actions"]
                    if isinstance(actions, str):
                        actions = actions.split(";")
                    actions_text = "; ".join(actions[:3]) if len(actions) > 3 else "; ".join(actions)
                    detail_rows.append([Paragraph("Recommended:", label_style), Paragraph(_wrap_text(actions_text, 80)[0] if len(_wrap_text(actions_text, 80)) > 0 else actions_text, card_text_style)])
                if score.get("residual_rpn") is not None:
                    detail_rows.append([Paragraph("Residual RPN:", label_style), Paragraph(str(score["residual_rpn"]), card_text_style)])

                if detail_rows:
                    fmea_detail = Table(detail_rows, colWidths=[doc.width * 0.25, doc.width * 0.75])
                    fmea_detail.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0dae2")),
                                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5ebf0")),
                                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                                ("TOPPADDING", (0, 0), (-1, -1), 4),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ]
                        )
                    )
                    story.append(KeepTogether([fmea_header, fmea_rpn_row, fmea_detail, Spacer(1, 3 * mm)]))
                else:
                    story.append(KeepTogether([fmea_header, fmea_rpn_row, Spacer(1, 3 * mm)]))

    # Robustness and Stress Testing
    section_num = "2" if is_enriched else "2"
    story.append(Paragraph(f"{section_num}. Robustness and Stress Testing", section_style))
    stress_results = report.get("stress_results", [])
    if stress_results:
        stress_rows = [[
            Paragraph("Case", label_style),
            Paragraph("Kind", label_style),
            Paragraph("Drop", label_style),
            Paragraph("Severity", label_style),
            Paragraph("Entropy", label_style),
        ]]
        for result in stress_results:
            performance_drop = float(result.get("performance_drop", 0.0))
            stress_rows.append(
                [
                    Paragraph(str(result.get("perturbation_name", "N/A")), card_text_style),
                    Paragraph(str(result.get("perturbation_kind", "N/A")), card_text_style),
                    Paragraph(f"{performance_drop:.3f}", card_text_style),
                    Paragraph(f"{float(result.get('severity', 0.0)):.2f}", card_text_style),
                    Paragraph(f"{float(result.get('average_entropy', 0.0)):.3f}", card_text_style),
                ]
            )

        stress_table = Table(
            stress_rows,
            colWidths=[doc.width * 0.32, doc.width * 0.15, doc.width * 0.14, doc.width * 0.14, doc.width * 0.25],
            repeatRows=1,
        )
        stress_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecf2f7")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0dae2")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5ebf0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(stress_table)
    else:
        story.append(Paragraph("No stress testing results available.", card_text_style))

    story.append(Spacer(1, 2.5 * mm))
    section_num = "3" if is_enriched else "3"
    story.append(Paragraph(f"{section_num}. Fairness and Bias Assessment (Art. 9.9)", section_style))
    fairness_results = report.get("fairness_results", [])
    fairness_critical = [
        item
        for item in fairness_results
        if "disparate_impact" in item.get("metric_name", "") or "equalized_odds_gap" in item.get("metric_name", "")
    ][:8]

    if fairness_critical:
        fairness_rows = [[Paragraph("Metric", label_style), Paragraph("Values", label_style)]]
        for item in fairness_critical:
            metric_name = item.get("metric_name", "metric").replace("_", " ").title()
            group_text = ", ".join(
                f"{group.get('group_name', 'group')}={float(group.get('value', 0.0)):.4f}"
                for group in item.get("groups", [])[:4]
            )
            fairness_rows.append(
                [
                    Paragraph(metric_name, card_text_style),
                    Paragraph(group_text if group_text else "N/A", card_text_style),
                ]
            )

        fairness_table = Table(fairness_rows, colWidths=[doc.width * 0.44, doc.width * 0.56], repeatRows=1)
        fairness_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecf2f7")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0dae2")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5ebf0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(fairness_table)
    else:
        story.append(Paragraph("No fairness metrics available.", card_text_style))

    story.append(Spacer(1, 2.5 * mm))
    section_num = "4" if is_enriched else "4"
    story.append(Paragraph(f"{section_num}. Transparency Card (Art. 13)", section_style))
    transparency_rows = [
        [Paragraph("Intended use", label_style), Paragraph("Declared by deployer in system setup", card_text_style)],
        [Paragraph("Known constraints", label_style), Paragraph("See fairness and robustness sections above", card_text_style)],
        [Paragraph("Recommended mitigations", label_style), Paragraph("See risk register strategies and action items", card_text_style)],
    ]
    transparency_table = Table(transparency_rows, colWidths=[doc.width * 0.26, doc.width * 0.74])
    transparency_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0dae2")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5ebf0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(transparency_table)

    story.append(Spacer(1, 4 * mm))
    total_risks = report.get("risk_register", {}).get("total_records", 0)
    fmea_count = len(report.get("fmea_scores", [])) if is_enriched else 0
    end_label = f"End of Report | Risks: {total_risks}" + (f" | FMEA Items: {fmea_count}" if is_enriched else "")
    end_bar = Table(
        [[Paragraph(end_label, centered_footer_style)]],
        colWidths=[doc.width],
    )
    end_bar.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#34495e")),
                ("BOX", (0, 0), (-1, -1), 0, colors.HexColor("#34495e")),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(end_bar)

    def _draw_page_footer(pdf_canvas, pdf_doc) -> None:
        pdf_canvas.saveState()
        pdf_canvas.setFont("Helvetica", 8)
        pdf_canvas.setFillColor(colors.HexColor("#7f8c8d"))
        pdf_canvas.drawRightString(pdf_doc.pagesize[0] - doc.rightMargin, 8 * mm, f"Page {pdf_doc.page}")
        pdf_canvas.restoreState()

    doc.build(story, onFirstPage=_draw_page_footer, onLaterPages=_draw_page_footer)
    return path


def _wrap_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    words = text.split()
    lines: list[str] = []
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