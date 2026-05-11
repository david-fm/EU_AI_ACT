from eu_ai_act.compliance import ComplianceAssessment, FMEAScore, RiskRecord, RiskRegister
from eu_ai_act.reporting import export_assessment_json, export_assessment_markdown, export_assessment_pdf


def test_assessment_roundtrip(tmp_path):
    register = RiskRegister()
    register.add(
        RiskRecord(
            risk_id="R-001",
            title="Low-light instability",
            description="Model degrades under low-light inputs.",
            severity=4,
            occurrence=3,
            detectability=2,
            strategy="mitigate",
        )
    )
    assessment = ComplianceAssessment(
        framework="keras",
        model_name="demo-model",
        risk_register=register,
        fmea_scores=[FMEAScore(severity=4, occurrence=3, detectability=2)],
    )

    json_path = export_assessment_json(assessment, tmp_path / "assessment.json")
    md_path = export_assessment_markdown(assessment, tmp_path / "assessment.md")
    pdf_path = export_assessment_pdf(assessment, tmp_path / "assessment.pdf")

    assert json_path.exists()
    assert md_path.exists()
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
    assert assessment.risk_register.records[0].rpn == 24
    assert assessment.to_dict()["framework"] == "keras"