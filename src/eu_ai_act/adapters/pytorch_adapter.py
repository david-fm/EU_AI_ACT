"""Adapters for PyTorch models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base import BatchPrediction
from .utils import to_python_data


@dataclass(slots=True)
class PyTorchModelAdapter:
    model: Any
    model_name: str = "pytorch-model"

    framework: str = "pytorch"

    def predict(self, inputs: Any) -> BatchPrediction:
        torch = _import_torch()
        self.model.eval()
        with torch.no_grad():
            tensor_inputs = _to_tensor(torch, inputs)
            raw_predictions = self.model(tensor_inputs)
        return BatchPrediction(scores=to_python_data(raw_predictions), metadata={"framework": self.framework})

    def get_model_metadata(self) -> dict[str, Any]:
        return {
            "framework": self.framework,
            "model_name": self.model_name,
            "class_name": self.model.__class__.__name__,
        }


def _import_torch():
    try:
        import torch
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError("PyTorch is not installed. Install the 'torch' extra to use this adapter.") from exc
    return torch


def _to_tensor(torch: Any, inputs: Any):
    if isinstance(inputs, torch.Tensor):
        return inputs
    if hasattr(inputs, "to_numpy"):
        inputs = inputs.to_numpy()
    if hasattr(inputs, "numpy"):
        try:
            inputs = inputs.numpy()
        except TypeError:
            pass
    return torch.as_tensor(inputs)