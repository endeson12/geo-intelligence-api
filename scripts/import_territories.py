"""Valida e importa limites territoriais com proveniência no PostGIS."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from geo_intelligence_api.database import SessionLocal

REQUIRED_METADATA = {
    "source",
    "source_url",
    "territorial_code",
    "name",
    "license",
    "acquired_at",
    "quality",
}


def parse_territory(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection" or len(payload.get("features", [])) != 1:
        raise ValueError("esperado FeatureCollection com exatamente uma feição")
    metadata = payload.get("metadata")
    missing = (
        REQUIRED_METADATA - metadata.keys() if isinstance(metadata, dict) else REQUIRED_METADATA
    )
    if not isinstance(metadata, dict) or missing:
        missing_text = ", ".join(sorted(missing)) if isinstance(metadata, dict) else "todos"
        raise ValueError(f"metadata de proveniência ausente: {missing_text}")
    geometry = payload["features"][0].get("geometry", {})
    if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError("o limite deve ser Polygon ou MultiPolygon")
    return {
        "code": str(metadata["territorial_code"]),
        "name": str(metadata["name"]),
        "source": str(metadata["source"]),
        "source_url": str(metadata["source_url"]),
        "license": str(metadata["license"]),
        "acquired_at": str(metadata["acquired_at"]),
        "quality": str(metadata["quality"]),
        "geometry": geometry,
    }


def import_territory(record: dict[str, Any]) -> None:
    params = {**record, "geometry": json.dumps(record["geometry"], separators=(",", ":"))}
    statement = text(
        """INSERT INTO territories
        (code, name, source, source_url, license, acquired_at, quality, geom)
        VALUES
        (:code, :name, :source, :source_url, :license, :acquired_at, :quality,
         ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326)))
        ON CONFLICT (code) DO UPDATE SET
          name = EXCLUDED.name,
          source = EXCLUDED.source,
          source_url = EXCLUDED.source_url,
          license = EXCLUDED.license,
          acquired_at = EXCLUDED.acquired_at,
          quality = EXCLUDED.quality,
          geom = EXCLUDED.geom,
          imported_at = now()"""
    )
    with SessionLocal() as db:
        db.execute(statement, params)
        db.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    record = parse_territory(args.path)
    import_territory(record)
    print(
        f"status=importado territorio={record['code']} nome={record['name']} "
        f"fonte={record['source']}"
    )


if __name__ == "__main__":
    main()
