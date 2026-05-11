"""Load datasets from disk into a normalized in-memory adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Sequence

import pandas as pd

from ..adapters import InMemoryDatasetAdapter

DatasetFormat = Literal["auto", "json", "csv"]


def load_dataset_adapter(
    input_path: str | Path,
    *,
    dataset_format: DatasetFormat = "auto",
    features_key: str = "features",
    labels_key: str = "labels",
    metadata_key: str = "metadata",
    feature_columns: Sequence[str] | None = None,
    label_column: str | None = None,
    metadata_columns: Sequence[str] | None = None,
) -> InMemoryDatasetAdapter:
    path = Path(input_path)
    resolved_format = _resolve_dataset_format(path, dataset_format)

    if resolved_format == "json":
        return _load_json_dataset(
            path,
            features_key=features_key,
            labels_key=labels_key,
            metadata_key=metadata_key,
            feature_columns=feature_columns,
            label_column=label_column,
            metadata_columns=metadata_columns,
        )

    return _load_csv_dataset(
        path,
        feature_columns=feature_columns,
        label_column=label_column,
        metadata_columns=metadata_columns,
    )


def _resolve_dataset_format(path: Path, dataset_format: DatasetFormat) -> Literal["json", "csv"]:
    if dataset_format != "auto":
        return dataset_format

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    return "json"


def _load_json_dataset(
    path: Path,
    *,
    features_key: str,
    labels_key: str,
    metadata_key: str,
    feature_columns: Sequence[str] | None,
    label_column: str | None,
    metadata_columns: Sequence[str] | None,
) -> InMemoryDatasetAdapter:
    payload = json.loads(path.read_text(encoding="utf-8"))

    # Schema A: explicit arrays with features/labels/metadata keys.
    if isinstance(payload, dict) and features_key in payload:
        features = payload[features_key]
        labels = payload.get(labels_key)
        metadata = payload.get(metadata_key)
        return InMemoryDatasetAdapter(features=features, labels=labels, metadata=metadata)

    # Schema B: list of row objects.
    if isinstance(payload, list):
        frame = pd.DataFrame(payload)
        return _dataframe_to_adapter(
            frame,
            feature_columns=feature_columns,
            label_column=label_column,
            metadata_columns=metadata_columns,
        )

    raise ValueError(
        "Unsupported JSON dataset format. Use a dict with 'features' key or a list of row objects."
    )


def _load_csv_dataset(
    path: Path,
    *,
    feature_columns: Sequence[str] | None,
    label_column: str | None,
    metadata_columns: Sequence[str] | None,
) -> InMemoryDatasetAdapter:
    frame = pd.read_csv(path)
    return _dataframe_to_adapter(
        frame,
        feature_columns=feature_columns,
        label_column=label_column,
        metadata_columns=metadata_columns,
    )


def _dataframe_to_adapter(
    frame: pd.DataFrame,
    *,
    feature_columns: Sequence[str] | None,
    label_column: str | None,
    metadata_columns: Sequence[str] | None,
) -> InMemoryDatasetAdapter:
    metadata_columns = list(metadata_columns or [])
    ignored = set(metadata_columns)
    if label_column:
        ignored.add(label_column)

    if feature_columns is None:
        numeric_columns = [
            name
            for name in frame.columns
            if name not in ignored and pd.api.types.is_numeric_dtype(frame[name])
        ]
        if not numeric_columns:
            raise ValueError(
                "Could not infer feature columns. Provide --feature-columns for non-numeric datasets."
            )
        feature_columns = numeric_columns

    missing = [name for name in feature_columns if name not in frame.columns]
    if missing:
        raise ValueError(f"Feature columns not found: {missing}")

    features = frame.loc[:, list(feature_columns)].values.tolist()
    labels = frame[label_column].tolist() if label_column else None

    metadata = None
    if metadata_columns:
        missing_metadata = [name for name in metadata_columns if name not in frame.columns]
        if missing_metadata:
            raise ValueError(f"Metadata columns not found: {missing_metadata}")
        metadata = frame.loc[:, metadata_columns].to_dict(orient="records")

    return InMemoryDatasetAdapter(features=features, labels=labels, metadata=metadata)