"""Domain-specific stress-test taxonomies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
import tomllib

from .stress import StressTestCase, default_stress_test_cases


@dataclass(frozen=True, slots=True)
class StressTaxonomyProfile:
    name: str
    description: str
    cases: list[StressTestCase]


def resolve_stress_test_cases(
    domain_name: str | None,
    *,
    model_metadata: dict[str, object] | None = None,
    metadata_fields: Sequence[str] | None = None,
    taxonomy_config_path: str | Path | None = None,
) -> list[StressTestCase]:
    profile = resolve_stress_taxonomy(
        domain_name,
        model_metadata=model_metadata,
        metadata_fields=metadata_fields,
        taxonomy_config_path=taxonomy_config_path,
    )
    return list(profile.cases)


def resolve_stress_taxonomy(
    domain_name: str | None,
    *,
    model_metadata: dict[str, object] | None = None,
    metadata_fields: Sequence[str] | None = None,
    taxonomy_config_path: str | Path | None = None,
) -> StressTaxonomyProfile:
    configured_profiles = _load_profiles_from_toml(taxonomy_config_path)
    normalized = _normalize_domain_name(domain_name)
    if normalized is None:
        normalized = _infer_domain_name(model_metadata=model_metadata, metadata_fields=metadata_fields)

    if normalized and normalized in configured_profiles:
        return configured_profiles[normalized]
    if normalized == "nih_chest_xrays":
        return _nih_chest_xrays_profile()
    if normalized == "autonomous_vehicles":
        return _autonomous_vehicle_profile()

    if "generic" in configured_profiles:
        return configured_profiles["generic"]

    return StressTaxonomyProfile(
        name="generic",
        description="Generic stress testing profile with balanced visual perturbations.",
        cases=default_stress_test_cases(),
    )


def _load_profiles_from_toml(taxonomy_config_path: str | Path | None) -> dict[str, StressTaxonomyProfile]:
    path = _resolve_taxonomy_path(taxonomy_config_path)
    if path is None:
        return {}

    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}

    profiles: dict[str, StressTaxonomyProfile] = {}
    raw_profiles = payload.get("stress_taxonomies", {})
    if not isinstance(raw_profiles, dict):
        return profiles

    for profile_name, raw_profile in raw_profiles.items():
        if not isinstance(raw_profile, dict):
            continue
        cases = _parse_cases(raw_profile.get("cases", []))
        if not cases:
            continue
        normalized_name = _normalize_domain_name(str(profile_name)) or str(profile_name)
        description = str(raw_profile.get("description", "Custom stress taxonomy profile."))
        profiles[normalized_name] = StressTaxonomyProfile(
            name=normalized_name,
            description=description,
            cases=cases,
        )
    return profiles


def _parse_cases(raw_cases: object) -> list[StressTestCase]:
    if not isinstance(raw_cases, list):
        return []

    parsed: list[StressTestCase] = []
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            continue
        name = raw_case.get("name")
        kind = raw_case.get("kind")
        if not isinstance(name, str) or not isinstance(kind, str):
            continue
        if kind not in {"noise", "blur", "occlusion", "illumination"}:
            continue

        severity = float(raw_case.get("severity", 0.35))
        severity = max(0.05, min(0.95, severity))
        parameters = raw_case.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}
        parsed.append(StressTestCase(name=name, kind=kind, severity=severity, parameters=parameters))
    return parsed


def _resolve_taxonomy_path(taxonomy_config_path: str | Path | None) -> Path | None:
    if taxonomy_config_path:
        candidate = Path(taxonomy_config_path)
        return candidate if candidate.exists() else None

    default_path = Path("stress_taxonomies.toml")
    return default_path if default_path.exists() else None


def _nih_chest_xrays_profile() -> StressTaxonomyProfile:
    return StressTaxonomyProfile(
        name="nih_chest_xrays",
        description="Radiology-oriented perturbations for NIH Chest X-rays style workflows.",
        cases=[
            StressTestCase(name="xray_sensor_noise", kind="noise", severity=0.22, parameters={"modality": "radiology"}),
            StressTestCase(
                name="xray_soft_blur",
                kind="blur",
                severity=0.34,
                parameters={"mode": "gaussian_like", "kernel_size": 5},
            ),
            StressTestCase(
                name="xray_central_occlusion",
                kind="occlusion",
                severity=0.38,
                parameters={"position": "center", "coverage": 0.30},
            ),
            StressTestCase(
                name="xray_low_light",
                kind="illumination",
                severity=0.30,
                parameters={"direction": -1, "modality": "radiology"},
            ),
        ],
    )


def _autonomous_vehicle_profile() -> StressTaxonomyProfile:
    return StressTaxonomyProfile(
        name="autonomous_vehicles",
        description="Driving-oriented perturbations for autonomous vehicle perception workflows.",
        cases=[
            StressTestCase(name="road_sensor_noise", kind="noise", severity=0.18, parameters={"context": "road"}),
            StressTestCase(
                name="road_motion_blur",
                kind="blur",
                severity=0.45,
                parameters={"mode": "motion_horizontal", "kernel_size": 7},
            ),
            StressTestCase(
                name="road_lateral_occlusion",
                kind="occlusion",
                severity=0.34,
                parameters={"position": "right", "coverage": 0.24},
            ),
            StressTestCase(
                name="road_glare",
                kind="illumination",
                severity=0.42,
                parameters={"direction": 1, "scenario": "glare"},
            ),
            StressTestCase(
                name="road_low_light",
                kind="illumination",
                severity=0.28,
                parameters={"direction": -1, "scenario": "night"},
            ),
        ],
    )


def _normalize_domain_name(domain_name: str | None) -> str | None:
    if not domain_name:
        return None

    value = domain_name.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "nih": "nih_chest_xrays",
        "nih_chest_xray": "nih_chest_xrays",
        "nih_chest_x_rays": "nih_chest_xrays",
        "nih_chest_xrays": "nih_chest_xrays",
        "chest_xray": "nih_chest_xrays",
        "chest_x_rays": "nih_chest_xrays",
        "chest_xrays": "nih_chest_xrays",
        "xray": "nih_chest_xrays",
        "x_rays": "nih_chest_xrays",
        "radiology": "nih_chest_xrays",
        "autonomous_vehicle": "autonomous_vehicles",
        "autonomous_vehicles": "autonomous_vehicles",
        "vehicle": "autonomous_vehicles",
        "vehicles": "autonomous_vehicles",
        "self_driving": "autonomous_vehicles",
        "self_driving_car": "autonomous_vehicles",
        "self_driving_vehicle": "autonomous_vehicles",
    }
    return aliases.get(value, value)


def _infer_domain_name(
    *,
    model_metadata: dict[str, object] | None = None,
    metadata_fields: Sequence[str] | None = None,
) -> str | None:
    fields = {field.strip().lower() for field in (metadata_fields or [])}
    model_name = str((model_metadata or {}).get("model_name", "")).lower()
    class_name = str((model_metadata or {}).get("class_name", "")).lower()

    if fields.intersection({"patient_age", "age", "sex", "view_position", "laterality", "study_id"}):
        return "nih_chest_xrays"
    if fields.intersection({"weather", "speed", "lane", "road_type", "camera_position", "intersection"}):
        return "autonomous_vehicles"

    haystack = f"{model_name} {class_name}"
    if any(token in haystack for token in ("xray", "chest", "radiology", "nih")):
        return "nih_chest_xrays"
    if any(token in haystack for token in ("vehicle", "driving", "autonomous", "road", "lane")):
        return "autonomous_vehicles"
    return None