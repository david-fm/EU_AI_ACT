"""Adapters for TensorFlow models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base import BatchPrediction
from .utils import normalize_batch_inputs, to_python_data


@dataclass(slots=True)
class TensorFlowModelAdapter:
    model: Any
    model_name: str = "tensorflow-model"

    framework: str = "tensorflow"

    def predict(self, inputs: Any) -> BatchPrediction:
        inputs = normalize_batch_inputs(inputs)
        if hasattr(self.model, "predict"):
            raw_predictions = self.model.predict(inputs, verbose=0)
        else:
            raw_predictions = self.model(inputs, training=False)
        return BatchPrediction(scores=to_python_data(raw_predictions), metadata={"framework": self.framework})

    def get_model_metadata(self) -> dict[str, Any]:
        return {
            "framework": self.framework,
            "model_name": self.model_name,
            "class_name": self.model.__class__.__name__,
        }