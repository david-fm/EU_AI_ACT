"""Load framework-specific models from disk and wrap them in adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .keras_adapter import KerasModelAdapter
from .pytorch_adapter import PyTorchModelAdapter
from .tensorflow_adapter import TensorFlowModelAdapter

FrameworkName = Literal["keras", "tensorflow", "pytorch"]


@dataclass(frozen=True, slots=True)
class LoadedModel:
    framework: FrameworkName
    model: Any
    model_name: str


def load_model_adapter(framework: FrameworkName, model_path: str | Path, model_name: str | None = None):
    """Load a model from disk and wrap it in the matching adapter."""

    path = Path(model_path)
    model_name = model_name or path.stem

    if framework == "keras":
        return KerasModelAdapter(model=_load_keras_model(path), model_name=model_name)
    if framework == "tensorflow":
        return TensorFlowModelAdapter(model=_load_tensorflow_model(path), model_name=model_name)
    return PyTorchModelAdapter(model=_load_pytorch_model(path), model_name=model_name)


def _load_keras_model(path: Path) -> Any:
    from keras.models import load_model

    return load_model(path)


def _load_tensorflow_model(path: Path) -> Any:
    import tensorflow as tf

    return tf.keras.models.load_model(path)


def _load_pytorch_model(path: Path) -> Any:
    torch = _import_torch()

    if path.suffix in {".pt", ".pth", ".torchscript"}:
        try:
            return torch.jit.load(str(path), map_location="cpu")
        except (RuntimeError, ValueError, AttributeError):
            return torch.load(str(path), map_location="cpu")

    loaded = torch.load(str(path), map_location="cpu")
    if hasattr(loaded, "eval"):
        return loaded
    raise RuntimeError(f"Unsupported PyTorch artifact at {path}: expected a model or scripted module.")


def _import_torch():
    try:
        import torch
    except ModuleNotFoundError as exc:  # pragma: no cover - optional extra
        raise RuntimeError("PyTorch is not installed. Install the 'torch' extra to load PyTorch models.") from exc
    return torch