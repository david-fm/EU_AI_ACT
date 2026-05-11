import json

import numpy as np

from eu_ai_act.adapters.base import BatchPrediction
from eu_ai_act.adapters import InMemoryDatasetAdapter, KerasModelAdapter, load_model_adapter
from eu_ai_act.evaluation import ComplianceEvaluator
from eu_ai_act.compliance.taxonomy import resolve_stress_test_cases


def test_compliance_evaluator_builds_assessment_with_risk_and_fairness():
    from keras import Sequential
    from keras import layers

    model = Sequential(
        [
            layers.Input(shape=(2,)),
            layers.Dense(1, kernel_initializer="ones", bias_initializer="zeros"),
        ]
    )
    adapter = KerasModelAdapter(model=model, model_name="eval-demo")
    dataset = InMemoryDatasetAdapter(
        features=[np.array([1.0, 2.0], dtype=np.float32), np.array([0.5, 0.5], dtype=np.float32)],
        labels=[1.0, 0.0],
        metadata=[{"site": "a"}, {"site": "b"}],
    )

    evaluator = ComplianceEvaluator(batch_size=2, prediction_threshold=0.5)
    assessment, summary = evaluator.evaluate(adapter, dataset)

    assert summary.sample_count == 2
    assert summary.batch_count == 1
    assert assessment.framework == "keras"
    assert assessment.model_name == "eval-demo"
    assert assessment.risk_register.records
    assert assessment.fairness_results
    assert assessment.to_dict()["risk_register"]["total_records"] >= 1


def test_cli_generates_reports(tmp_path):
    from eu_ai_act.cli import main

    from keras import Sequential
    from keras import layers

    model_path = tmp_path / "model.keras"
    model = Sequential(
        [
            layers.Input(shape=(2,)),
            layers.Dense(1, kernel_initializer="ones", bias_initializer="zeros"),
        ]
    )
    model.save(model_path)

    input_payload = {
        "features": [[1.0, 2.0], [0.0, 0.0]],
        "labels": [1.0, 0.0],
        "metadata": [{"site": "a"}, {"site": "b"}],
        "model_name": "cli-demo",
    }
    input_path = tmp_path / "input.json"
    output_dir = tmp_path / "out"
    input_path.write_text(json.dumps(input_payload), encoding="utf-8")

    exit_code = main([
        "--framework",
        "keras",
        "--model-path",
        str(model_path),
        "--input",
        str(input_path),
        "--output-dir",
        str(output_dir),
        "--batch-size",
        "1",
    ])

    assert exit_code == 0
    assert (output_dir / "assessment.json").exists()
    assert (output_dir / "assessment.md").exists()
    assert (output_dir / "assessment.pdf").exists()
    assert (output_dir / "assessment.pdf").stat().st_size > 0


def test_cli_generates_reports_from_csv_dataset(tmp_path):
    from eu_ai_act.cli import main

    from keras import Sequential
    from keras import layers

    model_path = tmp_path / "model_csv.keras"
    model = Sequential(
        [
            layers.Input(shape=(2,)),
            layers.Dense(1, kernel_initializer="ones", bias_initializer="zeros"),
        ]
    )
    model.save(model_path)

    csv_path = tmp_path / "dataset.csv"
    csv_path.write_text("f1,f2,target,site\n1.0,2.0,1,a\n0.0,0.0,0,b\n", encoding="utf-8")
    output_dir = tmp_path / "out_csv"

    exit_code = main([
        "--framework",
        "keras",
        "--model-path",
        str(model_path),
        "--input",
        str(csv_path),
        "--dataset-format",
        "csv",
        "--feature-columns",
        "f1",
        "f2",
        "--label-column",
        "target",
        "--metadata-columns",
        "site",
        "--output-dir",
        str(output_dir),
        "--batch-size",
        "1",
    ])

    assert exit_code == 0
    assert (output_dir / "assessment.json").exists()
    assert (output_dir / "assessment.md").exists()
    assert (output_dir / "assessment.pdf").exists()
    assert (output_dir / "assessment.pdf").stat().st_size > 0


def test_load_model_adapter_from_saved_keras_model(tmp_path):
    from keras import Sequential
    from keras import layers

    model_path = tmp_path / "saved.keras"
    model = Sequential(
        [
            layers.Input(shape=(2,)),
            layers.Dense(1, kernel_initializer="ones", bias_initializer="zeros"),
        ]
    )
    model.save(model_path)

    adapter = load_model_adapter("keras", model_path, model_name="loaded-keras")
    prediction = adapter.predict(np.array([[1.0, 2.0]], dtype=np.float32))

    assert adapter.get_model_metadata()["model_name"] == "loaded-keras"
    assert prediction.scores == [[3.0]]


def test_evaluator_computes_equalized_odds_and_disparate_impact():
    class StaticAdapter:
        framework = "keras"

        def __init__(self, scores):
            self._scores = scores
            self._cursor = 0

        def predict(self, inputs):
            batch_size = len(inputs)
            chunk = self._scores[self._cursor : self._cursor + batch_size]
            self._cursor += batch_size
            return BatchPrediction(scores=[[value] for value in chunk], metadata={"framework": "keras"})

        def get_model_metadata(self):
            return {"framework": "keras", "model_name": "static"}

    dataset = InMemoryDatasetAdapter(
        features=[[0.0], [1.0], [2.0], [3.0]],
        labels=[1, 0, 1, 0],
        metadata=[
            {"group": "A"},
            {"group": "A"},
            {"group": "B"},
            {"group": "B"},
        ],
    )
    model = StaticAdapter(scores=[0.9, 0.9, 0.9, 0.1])

    assessment, _ = ComplianceEvaluator(batch_size=2, prediction_threshold=0.5).evaluate(model, dataset)
    metrics_by_name = {item.metric_name: item for item in assessment.fairness_results}

    eo_metric = metrics_by_name["equalized_odds_gap_by_group"]
    di_metric = metrics_by_name["disparate_impact_ratio_by_group"]
    threshold_metric = metrics_by_name["optimal_threshold_by_group"]
    brier_metric = metrics_by_name["brier_score_by_group"]
    ece_metric = metrics_by_name["ece_by_group"]
    thresholded_eo_metric = metrics_by_name["equalized_odds_gap_group_thresholded_by_group"]
    thresholded_di_metric = metrics_by_name["disparate_impact_ratio_group_thresholded_by_group"]

    eo_values = {entry.group_name: entry.value for entry in eo_metric.groups}
    di_values = {entry.group_name: entry.value for entry in di_metric.groups}

    assert eo_values["tpr_gap"] == 0.0
    assert eo_values["fpr_gap"] == 1.0
    assert eo_values["equalized_odds_gap"] == 1.0
    assert di_values["ratio"] == 0.5
    assert len(threshold_metric.groups) == 2
    assert len(brier_metric.groups) == 2
    assert len(ece_metric.groups) == 2
    assert thresholded_eo_metric.groups[0].group_name == "equalized_odds_gap"
    assert thresholded_di_metric.groups[0].group_name == "ratio"


def test_evaluator_runs_stress_testing_and_builds_risks():
    class StressSensitiveAdapter:
        framework = "keras"

        def __init__(self):
            self._weights = np.array([[1.4, -1.1], [-1.0, 1.2]], dtype=np.float32)

        def predict(self, inputs):
            batch = np.asarray(inputs, dtype=np.float32)
            if batch.ndim == 2:
                batch = np.expand_dims(batch, axis=0)

            scores = []
            for sample in batch:
                raw_score = float(np.sum(sample * self._weights))
                probability = 1.0 / (1.0 + np.exp(-raw_score * 2.5))
                scores.append([float(probability)])
            return BatchPrediction(scores=scores, metadata={"framework": "keras"})

        def get_model_metadata(self):
            return {"framework": "keras", "model_name": "stress-sensitive"}

    dataset = InMemoryDatasetAdapter(
        features=[
            np.array([[1.0, 0.0], [1.0, 0.0]], dtype=np.float32),
            np.array([[0.0, 1.0], [0.0, 1.0]], dtype=np.float32),
        ],
        labels=[1, 0],
        metadata=[{"group": "A"}, {"group": "B"}],
    )

    assessment, summary = ComplianceEvaluator(batch_size=2, prediction_threshold=0.5).evaluate(
        StressSensitiveAdapter(),
        dataset,
    )

    assert summary.sample_count == 2
    assert len(assessment.stress_results) == 4
    assert {result.perturbation_name for result in assessment.stress_results} == {
        "noise",
        "blur",
        "occlusion",
        "illumination",
    }
    assert all(result.severity_points for result in assessment.stress_results)
    assert all(result.max_performance_drop >= result.performance_drop for result in assessment.stress_results)
    assert all(isinstance(result.drop_slope, float) for result in assessment.stress_results)
    assert any(len(result.severity_points) >= 2 for result in assessment.stress_results)
    assert any(record.risk_id.startswith("R-STRESS-") for record in assessment.risk_register.records)
    serialized_stress = assessment.to_dict()["stress_results"]
    assert serialized_stress
    assert all("severity_points" in item for item in serialized_stress)


def test_domain_taxonomies_are_distinct_and_resolvable():
    chest_cases = resolve_stress_test_cases("nih chest x-rays")
    vehicle_cases = resolve_stress_test_cases("autonomous vehicles")

    chest_names = {case.name for case in chest_cases}
    vehicle_names = {case.name for case in vehicle_cases}

    assert chest_names == {
        "xray_sensor_noise",
        "xray_soft_blur",
        "xray_central_occlusion",
        "xray_low_light",
    }
    assert vehicle_names == {
        "road_sensor_noise",
        "road_motion_blur",
        "road_lateral_occlusion",
        "road_glare",
        "road_low_light",
    }
    assert chest_names != vehicle_names


def test_evaluator_uses_domain_specific_stress_profile():
    class StaticAdapter:
        framework = "keras"

        def predict(self, inputs):
            batch = np.asarray(inputs, dtype=np.float32)
            if batch.ndim == 1:
                batch = np.expand_dims(batch, axis=0)

            scores = []
            for sample in batch:
                raw_score = float(np.sum(sample))
                probability = 1.0 / (1.0 + np.exp(-raw_score))
                scores.append([float(probability)])
            return BatchPrediction(scores=scores, metadata={"framework": "keras"})

        def get_model_metadata(self):
            return {"framework": "keras", "model_name": "xray-demo"}

    dataset = InMemoryDatasetAdapter(
        features=[[0.0], [1.0], [2.0], [3.0]],
        labels=[1, 0, 1, 0],
        metadata=[{"study_id": "1"}, {"study_id": "2"}, {"study_id": "3"}, {"study_id": "4"}],
    )
    model = StaticAdapter()

    assessment, summary = ComplianceEvaluator(batch_size=2, prediction_threshold=0.5, stress_domain="nih chest x-rays").evaluate(
        model,
        dataset,
    )

    assert summary.stress_domain == "nih_chest_xrays"
    assert summary.stress_case_names == [
        "xray_sensor_noise",
        "xray_soft_blur",
        "xray_central_occlusion",
        "xray_low_light",
    ]
    assert {result.perturbation_name for result in assessment.stress_results} == set(summary.stress_case_names)


def test_taxonomy_can_be_loaded_from_custom_toml(tmp_path):
    custom_toml = tmp_path / "custom_taxonomy.toml"
    custom_toml.write_text(
        """
[stress_taxonomies.nih_chest_xrays]
description = "Override profile"

[[stress_taxonomies.nih_chest_xrays.cases]]
name = "xray_custom_noise"
kind = "noise"
severity = 0.12

[stress_taxonomies.nih_chest_xrays.cases.parameters]
tag = "custom"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    cases = resolve_stress_test_cases("nih chest x-rays", taxonomy_config_path=custom_toml)

    assert len(cases) == 1
    assert cases[0].name == "xray_custom_noise"
    assert cases[0].parameters["tag"] == "custom"


def test_evaluator_uses_custom_toml_profile(tmp_path):
    class StaticAdapter:
        framework = "keras"

        def predict(self, inputs):
            batch = np.asarray(inputs, dtype=np.float32)
            if batch.ndim == 1:
                batch = np.expand_dims(batch, axis=0)
            scores = [[float(1.0 / (1.0 + np.exp(-float(np.sum(sample))))) ] for sample in batch]
            return BatchPrediction(scores=scores, metadata={"framework": "keras"})

        def get_model_metadata(self):
            return {"framework": "keras", "model_name": "xray-demo"}

    custom_toml = tmp_path / "custom_taxonomy.toml"
    custom_toml.write_text(
        """
[stress_taxonomies.nih_chest_xrays]
description = "Override profile"

[[stress_taxonomies.nih_chest_xrays.cases]]
name = "xray_custom_noise"
kind = "noise"
severity = 0.12
""".strip()
        + "\n",
        encoding="utf-8",
    )

    dataset = InMemoryDatasetAdapter(
        features=[[0.0], [1.0], [2.0], [3.0]],
        labels=[1, 0, 1, 0],
        metadata=[{"study_id": "1"}, {"study_id": "2"}, {"study_id": "3"}, {"study_id": "4"}],
    )

    assessment, summary = ComplianceEvaluator(
        batch_size=2,
        prediction_threshold=0.5,
        stress_domain="nih chest x-rays",
        stress_taxonomy_path=custom_toml,
    ).evaluate(StaticAdapter(), dataset)

    assert summary.stress_domain == "nih_chest_xrays"
    assert summary.stress_case_names == ["xray_custom_noise"]
    assert {result.perturbation_name for result in assessment.stress_results} == {"xray_custom_noise"}


def test_evaluator_generates_run_id_and_config_hash():
    class StaticAdapter:
        framework = "keras"

        def predict(self, inputs):
            batch_size = len(inputs)
            return BatchPrediction(scores=[[0.9] for _ in range(batch_size)], metadata={"framework": "keras"})

        def get_model_metadata(self):
            return {"framework": "keras", "model_name": "static-versioned"}

    dataset = InMemoryDatasetAdapter(
        features=[[0.0], [1.0]],
        labels=[1, 0],
        metadata=[{"group": "A"}, {"group": "B"}],
    )

    assessment, summary = ComplianceEvaluator(batch_size=2, prediction_threshold=0.5).evaluate(StaticAdapter(), dataset)

    assert summary.run_id is not None
    assert summary.run_id.startswith("run-")
    assert summary.config_hash is not None
    assert len(summary.config_hash) == 16
    serialized = assessment.to_dict()
    assert serialized["run_metadata"]["run_id"] == summary.run_id
    assert serialized["run_metadata"]["config_hash"] == summary.config_hash