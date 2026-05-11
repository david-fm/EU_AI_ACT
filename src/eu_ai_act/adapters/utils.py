"""Shared helpers for adapter normalization."""

from __future__ import annotations

from typing import Any

import numpy as np


def to_python_data(value: Any) -> Any:
    """Convert tensors, arrays, and nested structures into serializable Python data."""

    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        try:
            value = value.numpy()
        except TypeError:
            pass
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {key: to_python_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_python_data(item) for item in value]
    return value


def ensure_batch_list(inputs: Any) -> list[Any]:
    """Normalize a single sample or batch-like input to a Python list."""

    if isinstance(inputs, (list, tuple)):
        return list(inputs)
    return [inputs]


def normalize_batch_inputs(inputs: Any) -> Any:
    """Convert homogeneous lists of samples into a stacked batch array when possible."""

    if isinstance(inputs, (list, tuple)) and inputs:
        if any(isinstance(item, dict) for item in inputs):
            return inputs
        try:
            return np.asarray(inputs)
        except ValueError:
            return inputs
    return inputs