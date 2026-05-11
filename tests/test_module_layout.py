from eu_ai_act.core import ComplianceEvaluator, ComplianceAssessment
from eu_ai_act.operations import compare_assessments


def test_core_and_operations_modules_are_importable():
    assert ComplianceEvaluator is not None
    assert ComplianceAssessment is not None
    assert callable(compare_assessments)
