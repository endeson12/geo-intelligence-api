"""Gera relatório reproduzível de qualidade para FeatureCollections de pontos."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def analyze_feature_collection(payload: dict[str, Any]) -> dict[str, Any]:
    """Valida estrutura, coordenadas, campos essenciais e duplicidades."""
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    types: Counter[str] = Counter()
    coordinates: list[tuple[float, float]] = []
    seen: set[tuple[str, str, float, float]] = set()
    duplicate_count = 0

    if payload.get("type") != "FeatureCollection":
        errors.append(
            {"code": "invalid_collection_type", "message": "type deve ser FeatureCollection"}
        )

    features = payload.get("features")
    if not isinstance(features, list):
        return {
            "status": "reprovado",
            "feature_count": 0,
            "valid_feature_count": 0,
            "duplicate_count": 0,
            "type_counts": {},
            "bbox": None,
            "errors": errors
            + [{"code": "features_not_array", "message": "features deve ser uma lista"}],
            "warnings": warnings,
        }

    for index, feature in enumerate(features):
        if not isinstance(feature, dict):
            errors.append(
                {"index": index, "code": "invalid_feature", "message": "feição deve ser objeto"}
            )
            continue

        geometry = feature.get("geometry") or {}
        properties = feature.get("properties") or {}
        if geometry.get("type") != "Point":
            errors.append(
                {"index": index, "code": "invalid_geometry", "message": "apenas Point é aceito"}
            )
            continue

        point = geometry.get("coordinates")
        if (
            not isinstance(point, list)
            or len(point) != 2
            or not all(isinstance(value, (int, float)) for value in point)
        ):
            errors.append(
                {
                    "index": index,
                    "code": "invalid_coordinates",
                    "message": "coordenadas devem ser [lon, lat] numéricas",
                }
            )
            continue

        lon, lat = float(point[0]), float(point[1])
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            errors.append(
                {"index": index, "code": "out_of_wgs84", "message": "coordenadas fora de EPSG:4326"}
            )
            continue

        missing = [field for field in ("nome", "tipo", "fonte") if not properties.get(field)]
        if missing:
            errors.append({"index": index, "code": "missing_properties", "fields": missing})
            continue

        name = str(properties["nome"]).strip()
        facility_type = str(properties["tipo"]).strip()
        source = str(properties["fonte"]).strip()
        key = (name.casefold(), facility_type.casefold(), round(lon, 7), round(lat, 7))
        if key in seen:
            duplicate_count += 1
            warnings.append(
                {
                    "index": index,
                    "code": "possible_duplicate",
                    "message": "mesmo nome, tipo e coordenadas",
                }
            )
        else:
            seen.add(key)

        if "OpenStreetMap contributors" not in source:
            warnings.append(
                {
                    "index": index,
                    "code": "source_review",
                    "message": "atribuição OSM não identificada na fonte",
                }
            )

        types[facility_type] += 1
        coordinates.append((lon, lat))

    bbox = None
    if coordinates:
        lons, lats = zip(*coordinates, strict=True)
        bbox = [min(lons), min(lats), max(lons), max(lats)]

    return {
        "status": "aprovado" if not errors else "reprovado",
        "feature_count": len(features),
        "valid_feature_count": len(coordinates),
        "duplicate_count": duplicate_count,
        "type_counts": dict(sorted(types.items())),
        "bbox": bbox,
        "source_metadata": payload.get("metadata", {}),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("docs/data-quality-report.json"))
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = analyze_feature_collection(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"status={report['status']} features={report['feature_count']} "
        f"validas={report['valid_feature_count']} duplicadas={report['duplicate_count']}"
    )
    raise SystemExit(0 if report["status"] == "aprovado" else 1)


if __name__ == "__main__":
    main()
