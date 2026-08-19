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
from geo_intelligence_api.models import Facility

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGIS_INTEGRATION") != "1",
    reason="requer PostgreSQL/PostGIS migrado",
)


@pytest.fixture(autouse=True)
def limpar_facilities() -> Iterator[None]:
    with SessionLocal() as db:
        db.execute(delete(Facility))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(Facility))
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
    assert coverage.json()["total"] == 1

    imported = client.post(
        "/api/v1/import/geojson",
        headers={"X-API-Key": os.environ["API_KEY"]},
        json={
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
                }
            ],
        },
    )
    assert imported.status_code == 201
    assert imported.json() == {"importados": 1}
