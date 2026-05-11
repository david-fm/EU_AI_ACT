"""Adapters for Keras models and simple in-memory datasets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .base import BatchPrediction
from .utils import ensure_batch_list, normalize_batch_inputs, to_python_data


@dataclass(slots=True)
class KerasModelAdapter:
    model: Any
    model_name: str = "keras-model"

    framework: str = "keras"

    def predict(self, inputs: Any) -> BatchPrediction:
        raw_predictions = self.model.predict(normalize_batch_inputs(inputs), verbose=0)
        return BatchPrediction(scores=to_python_data(raw_predictions), metadata={"framework": self.framework})

    def get_model_metadata(self) -> dict[str, Any]:
        return {
            "framework": self.framework,
            "model_name": self.model_name,
            "class_name": self.model.__class__.__name__,
        }


@dataclass(slots=True)
class InMemoryDatasetAdapter:
    features: Sequence[Any]
    labels: Sequence[Any] | None = None
    metadata: Sequence[dict[str, Any]] | None = None

    def iter_batches(self, batch_size: int):
        total = len(self.features)
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch_features = list(self.features[start:end])
            batch_labels = None if self.labels is None else list(self.labels[start:end])
            batch_metadata = None if self.metadata is None else list(self.metadata[start:end])
            yield batch_features, batch_labels, batch_metadata

    def get_metadata_fields(self) -> Sequence[str]:
        if not self.metadata:
            return ()
        fields: list[str] = []
        for item in self.metadata:
            for key in item:
                if key not in fields:
                    fields.append(key)
        return tuple(fields)


def build_keras_in_memory_batches(features: Sequence[Any]) -> list[list[Any]]:
    """Convenience helper for tests and notebooks."""

    return [ensure_batch_list(item) for item in features]