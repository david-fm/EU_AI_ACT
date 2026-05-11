"""Shared interfaces for framework-specific adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class BatchPrediction:
    """Normalized prediction output used by the compliance layer."""

    scores: Sequence[Any]
    labels: Sequence[str] | None = None
    metadata: dict[str, Any] | None = None


class ModelAdapter(Protocol):
    """Common interface for Keras, TensorFlow, and PyTorch models."""

    framework: str

    def predict(self, inputs: Any) -> BatchPrediction:
        """Run inference and return normalized predictions."""

    def get_model_metadata(self) -> dict[str, Any]:
        """Return model name, version, and framework metadata."""


class DatasetAdapter(Protocol):
    """Common interface for datasets consumed by the compliance layer."""

    def iter_batches(self, batch_size: int):
        """Yield batches with features, labels, and optional metadata."""

    def get_metadata_fields(self) -> Sequence[str]:
        """Return the names of metadata fields available for fairness checks."""