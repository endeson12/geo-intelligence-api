import json
from pathlib import Path

import pytest

from scripts.import_territories import parse_territories, parse_territory

SOURCE = Path("data/ibge-teresina-boundary.geojson")


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

    with pytest.raises(ValueError, match="coordenadas fora dos limites WGS84"):
        parse_territory(file)


def test_rejeita_limite_com_coordenadas_3d(tmp_path: Path) -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    payload["features"][0]["geometry"]["coordinates"] = [
        [[-43.0, -5.0, 100], [-42.0, -5.0, 100], [-42.0, -4.0, 100], [-43.0, -5.0, 100]]
    ]
    path = tmp_path / "three-dimensional.geojson"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="coordenadas devem ser bidimensionais"):
        parse_territory(path)


def test_parse_colecao_de_bairros_com_metadados_por_feicao(tmp_path: Path) -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    geometry = payload["features"][0]["geometry"]
    payload["metadata"].pop("territorial_code")
    payload["metadata"].pop("name")
    payload["metadata"].update({"territory_type": "bairro", "parent_code": "2211001"})
    payload["features"] = [
        {
            "type": "Feature",
            "properties": {"territorial_code": "2211001001", "name": "Bairro A"},
            "geometry": geometry,
        },
        {
            "type": "Feature",
            "properties": {"territorial_code": "2211001002", "name": "Bairro B"},
            "geometry": geometry,
        },
    ]
    path = tmp_path / "neighborhoods.geojson"
    path.write_text(json.dumps(payload), encoding="utf-8")

    records = parse_territories(path)

    assert [record["code"] for record in records] == ["2211001001", "2211001002"]
    assert all(record["territory_type"] == "bairro" for record in records)
    assert all(record["parent_code"] == "2211001" for record in records)


def test_dataset_oficial_de_bairros_de_teresina() -> None:
    path = Path("data/ibge-teresina-neighborhoods.geojson")
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = parse_territories(path)

    assert len(records) == 123
    assert len({record["code"] for record in records}) == 123
    assert payload["metadata"]["source_crs"] == "EPSG:4674"
    assert payload["metadata"]["crs"] == "EPSG:4326"
    assert payload["metadata"]["source_sha256"] == (
        "cfd26ee37c8ca666e12eb5719ebdb2e0f7b108ded722cadc716e2ee82e347309"
    )
    assert all(record["parent_code"] == "2211001" for record in records)
