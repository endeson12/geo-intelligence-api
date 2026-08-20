"""Valida e importa limites territoriais com proveniência no PostGIS."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.validation import explain_validity
from sqlalchemy import text

from geo_intelligence_api.database import SessionLocal

REQUIRED_METADATA = {
    "source",
    "source_url",
    "license",
    "acquired_at",
    "quality",
    "crs",
}


def _validated_geometry(feature: dict[str, Any], crs: str) -> dict[str, Any]:
    geometry = feature.get("geometry", {})
    if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError("o limite deve ser Polygon ou MultiPolygon")
    if crs != "EPSG:4326":
        raise ValueError("CRS incompatível: esperado EPSG:4326")
    territorial_geometry = shape(geometry)
    if territorial_geometry.has_z:
        raise ValueError("coordenadas devem ser bidimensionais")
    if territorial_geometry.is_empty or not territorial_geometry.is_valid:
        reason = (
            "geometria vazia"
            if territorial_geometry.is_empty
            else explain_validity(territorial_geometry)
        )
        raise ValueError(f"geometria territorial inválida: {reason}")
    bounds = territorial_geometry.bounds
    min_lon, min_lat, max_lon, max_lat = bounds
    if not all(math.isfinite(value) for value in bounds) or not (
        -180 <= min_lon <= max_lon <= 180 and -90 <= min_lat <= max_lat <= 90
    ):
        raise ValueError("coordenadas fora dos limites WGS84")
    return geometry


def parse_territories(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = payload.get("features", [])
    if payload.get("type") != "FeatureCollection" or not isinstance(features, list) or not features:
        raise ValueError("esperado FeatureCollection com pelo menos uma feição")
    metadata = payload.get("metadata")
    missing = (
        REQUIRED_METADATA - metadata.keys() if isinstance(metadata, dict) else REQUIRED_METADATA
    )
    if not isinstance(metadata, dict) or missing:
        missing_text = ", ".join(sorted(missing)) if isinstance(metadata, dict) else "todos"
        raise ValueError(f"metadata de proveniência ausente: {missing_text}")

    crs = str(metadata["crs"]).upper()
    records: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for feature in features:
        properties = feature.get("properties") or {}
        code = properties.get("territorial_code") or metadata.get("territorial_code")
        name = properties.get("name") or metadata.get("name")
        if not code or not name:
            raise ValueError("territorial_code e name são obrigatórios por coleção ou feição")
        code = str(code)
        if code in seen_codes:
            raise ValueError(f"código territorial duplicado: {code}")
        seen_codes.add(code)
        records.append(
            {
                "code": code,
                "name": str(name),
                "source": str(metadata["source"]),
                "source_url": str(metadata["source_url"]),
                "license": str(metadata["license"]),
                "acquired_at": str(metadata["acquired_at"]),
                "quality": str(metadata["quality"]),
                "crs": crs,
                "territory_type": str(
                    properties.get("territory_type")
                    or metadata.get("territory_type")
                    or "municipio"
                ),
                "parent_code": properties.get("parent_code") or metadata.get("parent_code"),
                "geometry": _validated_geometry(feature, crs),
            }
        )
    return records


def parse_territory(path: Path) -> dict[str, Any]:
    records = parse_territories(path)
    if len(records) != 1:
        raise ValueError("esperado FeatureCollection com exatamente uma feição")
    return records[0]


def _statement() -> Any:
    return text(
        """INSERT INTO territories
        (code, name, source, source_url, license, acquired_at, quality,
         territory_type, parent_code, geom)
        VALUES
        (:code, :name, :source, :source_url, :license, :acquired_at, :quality,
         :territory_type, :parent_code,
         ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326)))
        ON CONFLICT (code) DO UPDATE SET
          name = EXCLUDED.name,
          source = EXCLUDED.source,
          source_url = EXCLUDED.source_url,
          license = EXCLUDED.license,
          acquired_at = EXCLUDED.acquired_at,
          quality = EXCLUDED.quality,
          territory_type = EXCLUDED.territory_type,
          parent_code = EXCLUDED.parent_code,
          geom = EXCLUDED.geom,
          imported_at = now()"""
    )


def import_territories(records: list[dict[str, Any]]) -> None:
    statement = _statement()
    with SessionLocal() as db:
        for record in records:
            params = {
                **record,
                "geometry": json.dumps(record["geometry"], separators=(",", ":")),
            }
            db.execute(statement, params)
        db.commit()


def import_territory(record: dict[str, Any]) -> None:
    import_territories([record])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    records = parse_territories(args.path)
    import_territories(records)
    print(
        f"status=importado territorios={len(records)} "
        f"tipo={records[0]['territory_type']} fonte={records[0]['source']}"
    )


if __name__ == "__main__":
    main()
