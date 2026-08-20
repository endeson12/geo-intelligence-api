import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import delete

from geo_intelligence_api.config import get_settings
from geo_intelligence_api.database import SessionLocal
from geo_intelligence_api.main import app
from geo_intelligence_api.models import DatasetBatch, Facility

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGIS_INTEGRATION") != "1",
    reason="requer PostgreSQL/PostGIS migrado",
)


@pytest.fixture(autouse=True)
def limpar_facilities() -> Iterator[None]:
    with SessionLocal() as db:
        db.execute(delete(Facility))
        db.execute(delete(DatasetBatch))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(Facility))
        db.execute(delete(DatasetBatch))
        db.commit()


def test_consultas_e_importacao_em_postgis_real() -> None:
    with SessionLocal() as db:
        db.add_all(
            [
                Facility(
                    nome="Unidade A",
                    tipo="saude",
                    fonte="integração",
                    geom=from_shape(Point(-42.80, -5.09), srid=4326),
                ),
                Facility(
                    nome="Unidade B",
                    tipo="educacao",
                    fonte="integração",
                    geom=from_shape(Point(-42.90, -5.20), srid=4326),
                ),
            ]
        )
        db.commit()

    get_settings.cache_clear()
    client = TestClient(app)

    nearest = client.get(
        "/api/v1/facilities/nearest",
        params={"lat": -5.091, "lon": -42.801, "raio_m": 5_000},
    )
    assert nearest.status_code == 200
    assert [feature["properties"]["nome"] for feature in nearest.json()["features"]] == [
        "Unidade A"
    ]
    assert nearest.json()["features"][0]["properties"]["distancia_m"] > 0

    coverage = client.get(
        "/api/v1/coverage",
        params={"lat": -5.091, "lon": -42.801, "raio_m": 5_000, "tipo": "saude"},
    )
    assert coverage.status_code == 200
    assert coverage.json()["type"] == "FeatureCollection"
    assert coverage.json()["summary"]["total"] == 1
    assert coverage.json()["features"][0]["properties"]["nome"] == "Unidade A"

    import_payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "nome": "Unidade C",
                    "tipo": "assistencia",
                    "fonte": "teste de integração",
                },
                "geometry": {"type": "Point", "coordinates": [-42.79, -5.08]},
            },
            {
                "type": "Feature",
                "properties": {
                    "nome": "Unidade D",
                    "tipo": "assistencia",
                    "fonte": "teste de integração",
                },
                "geometry": {"type": "Point", "coordinates": [-42.78, -5.07]},
            },
        ],
    }
    imported = client.post(
        "/api/v1/import/geojson",
        headers={"X-API-Key": os.environ["API_KEY"]},
        json=import_payload,
    )
    assert imported.status_code == 201
    assert imported.json()["status"] == "importado"
    assert imported.json()["importados"] == 2
    assert len(imported.json()["dataset_hash"]) == 64

    repeated = client.post(
        "/api/v1/import/geojson",
        headers={"X-API-Key": os.environ["API_KEY"]},
        json=import_payload,
    )
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "ja_importado"
    assert repeated.json()["importados"] == 0
    assert repeated.json()["duplicados"] == 2

    first_page = client.get(
        "/api/v1/territories/2211001/coverage", params={"limit": 1, "offset": 0}
    )
    assert first_page.status_code == 200
    first_body = first_page.json()
    total = first_body["resumo"]["total"]
    assert total >= 3
    assert first_body["territorio"]["fonte"].startswith("IBGE")
    assert first_body["territorio"]["geometry"]["type"] == "MultiPolygon"

    paged_ids: list[int] = []
    for offset in range(total):
        page = client.get(
            "/api/v1/territories/2211001/coverage",
            params={"limit": 1, "offset": offset},
        )
        assert page.status_code == 200
        body = page.json()
        paged_ids.append(body["equipamentos"]["features"][0]["id"])
        assert body["resumo"]["total"] == total
        assert body["resumo"]["retornados"] == 1
        assert body["resumo"]["tem_proxima_pagina"] is (offset + 1 < total)

    assert paged_ids == sorted(paged_ids)
    assert len(set(paged_ids)) == total

    filtered_pages = [
        client.get(
            "/api/v1/territories/2211001/coverage",
            params={"tipo": "assistencia", "limit": 1, "offset": offset},
        ).json()
        for offset in (0, 1)
    ]
    assert [page["resumo"]["total"] for page in filtered_pages] == [2, 2]
    assert [page["resumo"]["tem_proxima_pagina"] for page in filtered_pages] == [True, False]
    assert [
        page["equipamentos"]["features"][0]["properties"]["nome"] for page in filtered_pages
    ] == ["Unidade C", "Unidade D"]

    neighborhoods = client.get(
        "/api/v1/territories",
        params={"territory_type": "bairro", "parent_code": "2211001", "limit": 200},
    )
    assert neighborhoods.status_code == 200
    assert len(neighborhoods.json()) == 123
    assert {item["codigo"] for item in neighborhoods.json()} >= {"2211001094", "2211001083"}
    assert all(item["codigo_pai"] == "2211001" for item in neighborhoods.json())
