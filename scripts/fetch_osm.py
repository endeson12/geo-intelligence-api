"""Coleta equipamentos de saúde do OpenStreetMap via Overpass e gera GeoJSON.

A coleta é opcional e depende de rede. O arquivo resultante preserva o ID OSM e
atribuição ODbL; ele não deve ser tratado como cadastro oficial ou completo.
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
QUERY = """[out:json][timeout:25];
area["name"="Teresina"]["boundary"="administrative"]->.a;
(nwr["amenity"~"hospital|clinic|doctors"](area.a););
out center;
"""
TYPE_NAMES = {
    "hospital": "hospital",
    "clinic": "clinica",
    "doctors": "consultorio",
}


def to_feature_collection(payload: dict[str, Any]) -> dict[str, Any]:
    """Converte a resposta Overpass em FeatureCollection compatível com a API."""
    features: list[dict[str, Any]] = []
    timestamp = payload.get("osm3s", {}).get("timestamp_osm_base", "não informado")

    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        amenity = tags.get("amenity")
        name = tags.get("name")
        center = element.get("center", {})
        lat = element.get("lat", center.get("lat"))
        lon = element.get("lon", center.get("lon"))
        if amenity not in TYPE_NAMES or not name or lat is None or lon is None:
            continue

        osm_ref = f"{element.get('type', 'element')}/{element.get('id', 'sem-id')}"
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "nome": name,
                    "tipo": TYPE_NAMES[amenity],
                    "fonte": (
                        f"OpenStreetMap contributors (ODbL), snapshot {timestamp}; osm:{osm_ref}"
                    ),
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "metadata": {
            "source": "OpenStreetMap contributors",
            "license": "ODbL 1.0",
            "generated_from": "Overpass API",
            "timestamp_osm_base": timestamp,
            "warning": "Amostra comunitária; não é cadastro oficial nem garantia de completude.",
        },
        "features": features,
    }


def fetch() -> dict[str, Any]:
    """Executa a consulta pública com identificação explícita do cliente."""
    url = f"{OVERPASS_URL}?{urllib.parse.urlencode({'data': QUERY})}"
    request = urllib.request.Request(  # noqa: S310
        url,
        headers={"User-Agent": "geo-intelligence-api/0.2 (+https://github.com/endeson12)"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/osm-teresina-health.geojson"),
    )
    args = parser.parse_args()

    result = to_feature_collection(fetch())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{len(result['features'])} feições gravadas em {args.output}")


if __name__ == "__main__":
    main()
