from eu_ai_act.compliance import ComplianceAssessment, FMEAScore, RiskRecord, RiskRegister
from eu_ai_act.reporting import export_assessment_json, export_assessment_markdown


def test_assessment_serialization_contains_run_metadata_and_comparison(tmp_path):
    register = RiskRegister()
    register.add(
        RiskRecord(
            risk_id="R-001",
            title="Example risk",
            description="Example description",
            severity=4,
            occurrence=3,
            detectability=2,
            strategy="mitigate",
        )
    )

    assessment = ComplianceAssessment(
        framework="keras",
        model_name="demo-model",
        run_id="run-demo-1",
        config_hash="abcd1234efgh5678",
        risk_register=register,
        fmea_scores=[
            FMEAScore(
                severity=6,
                occurrence=4,
                detectability=5,
                failure_mode="mode",
                root_cause="cause",
                current_controls="controls",
                recommended_actions="actions",
                residual_rpn=90,
                action_required=True,
            )
        ],
        comparison_to_previous_run={"risk_total_delta": -1},
    )

    payload = assessment.to_dict()
    assert payload["run_metadata"]["run_id"] == "run-demo-1"
    assert payload["run_metadata"]["config_hash"] == "abcd1234efgh5678"
    assert payload["comparison_to_previous_run"]["risk_total_delta"] == -1

    json_path = export_assessment_json(assessment, tmp_path / "assessment.json")
    md_path = export_assessment_markdown(assessment, tmp_path / "assessment.md")

    assert json_path.exists()
    assert md_path.exists()

    markdown_text = md_path.read_text(encoding="utf-8")
    assert "Run ID: run-demo-1" in markdown_text
    assert "## Run Comparison" in markdown_text
    assert "risk_total_delta: -1" in markdown_text
