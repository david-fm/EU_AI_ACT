import json

from eu_ai_act.data import load_dataset_adapter


def test_load_dataset_adapter_json_payload(tmp_path):
    payload = {
        "features": [[1.0, 2.0], [0.0, 0.0]],
        "labels": [1, 0],
        "metadata": [{"site": "a"}, {"site": "b"}],
    }
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    dataset = load_dataset_adapter(path)
    batches = list(dataset.iter_batches(batch_size=2))

    assert len(batches) == 1
    assert batches[0][0] == [[1.0, 2.0], [0.0, 0.0]]
    assert batches[0][1] == [1, 0]
    assert dataset.get_metadata_fields() == ("site",)


def test_load_dataset_adapter_csv_columns(tmp_path):
    csv_content = "f1,f2,target,site\n1.0,2.0,1,a\n0.0,0.0,0,b\n"
    path = tmp_path / "dataset.csv"
    path.write_text(csv_content, encoding="utf-8")

    dataset = load_dataset_adapter(
        path,
        dataset_format="csv",
        feature_columns=["f1", "f2"],
        label_column="target",
        metadata_columns=["site"],
    )
    batches = list(dataset.iter_batches(batch_size=1))

    assert len(batches) == 2
    assert batches[0][0] == [[1.0, 2.0]]
    assert batches[0][1] == [1]
    assert batches[0][2] == [{"site": "a"}]