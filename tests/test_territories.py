import json
from pathlib import Path

import pytest

from scripts.import_territories import parse_territory


def test_parse_limite_oficial_do_ibge() -> None:
    record = parse_territory(Path("data/ibge-teresina-boundary.geojson"))

    assert record["code"] == "2211001"
    assert record["name"] == "Teresina"
    assert record["source"].startswith("IBGE")
    assert record["geometry"]["type"] == "Polygon"
    assert record["crs"] == "EPSG:4326"


def test_rejeita_limite_sem_proveniencia(tmp_path: Path) -> None:
    file = tmp_path / "boundary.geojson"
    file.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="metadata"):
        parse_territory(file)


def test_rejeita_limite_topologicamente_invalido(tmp_path: Path) -> None:
    payload = json.loads(Path("data/ibge-teresina-boundary.geojson").read_text(encoding="utf-8"))
    payload["features"][0]["geometry"] = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]],
    }
    file = tmp_path / "invalid-boundary.geojson"
    file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="geometria territorial inválida"):
        parse_territory(file)


def test_rejeita_limite_fora_da_faixa_wgs84(tmp_path: Path) -> None:
    payload = json.loads(Path("data/ibge-teresina-boundary.geojson").read_text(encoding="utf-8"))
    payload["features"][0]["geometry"] = {
        "type": "Polygon",
        "coordinates": [[[181, 0], [182, 0], [182, 1], [181, 0]]],
    }
    file = tmp_path / "out-of-range.geojson"
    file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="fora dos limites WGS84"):
        parse_territory(file)
