from typing import Any

from fastapi.testclient import TestClient

from geo_intelligence_api.database import get_db
from geo_intelligence_api.main import app


class Result:
    def __init__(self, rows: list[Any] | None = None, scalar: Any = 1) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self) -> "Result":
        return self

    def all(self) -> list[Any]:
        return self._rows

    def scalar_one(self) -> Any:
        return self._scalar


class FakeDB:
    def __init__(self, rows: list[Any] | None = None) -> None:
        self.rows = rows or []
        self.committed = False
        self.rolled_back = False
        self.queries: list[str] = []

    def execute(self, statement: Any, *_args: Any, **_kwargs: Any) -> Result:
        self.queries.append(str(statement))
        return Result(self.rows)

    def add_all(self, _items: list[Any]) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def test_live_e_headers() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live", headers={"X-Request-ID": "teste-123"})
    assert response.status_code == 200
    assert response.json() == {"status": "vivo"}
    assert response.headers["x-request-id"] == "teste-123"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_ready_com_banco() -> None:
    db = FakeDB()
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).get("/health/ready")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "pronto"


def test_facilities_retorna_feature_collection() -> None:
    rows = [{"id": 1, "nome": "UBS Teste", "tipo": "saude", "lon": -42.8, "lat": -5.1}]
    db = FakeDB(rows)
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).get("/api/v1/facilities?tipo=saude&bbox=-43,-6,-42,-4")
    finally:
        app.dependency_overrides.clear()
    body = response.json()
    assert response.status_code == 200
    assert body["type"] == "FeatureCollection"
    assert body["features"][0]["geometry"]["coordinates"] == [-42.8, -5.1]


def test_nearest_usa_operacoes_postgis() -> None:
    db = FakeDB()
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).get("/api/v1/facilities/nearest?lat=-5.09&lon=-42.8&limit=3")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert "ST_DWithin" in db.queries[0]
    assert "ST_DistanceSphere" in db.queries[0]


def test_coverage_retorna_contagem() -> None:
    db = FakeDB()
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).get(
            "/api/v1/coverage?lat=-5.09&lon=-42.8&raio_m=1000&tipo=saude"
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert "ST_DWithin" in db.queries[0]


def test_bbox_invalido_e_rejeitado() -> None:
    db = FakeDB()
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).get("/api/v1/facilities?bbox=-42,-5,-43,-6")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_import_exige_api_key() -> None:
    response = TestClient(app).post(
        "/api/v1/import/geojson", json={"type": "FeatureCollection", "features": []}
    )
    assert response.status_code == 401


def test_import_rejeita_geojson_invalido() -> None:
    response = TestClient(app).post(
        "/api/v1/import/geojson",
        headers={"X-API-Key": "change-me"},
        json={
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"nome": "X", "tipo": "saude"},
                    "geometry": {"type": "Point", "coordinates": [181, -5]},
                }
            ],
        },
    )
    assert response.status_code == 422


def test_import_valido_e_atomico() -> None:
    db = FakeDB()
    app.dependency_overrides[get_db] = lambda: db
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "nome": "Escola sintética",
                    "tipo": "educacao",
                    "fonte": "sintetico",
                },
                "geometry": {"type": "Point", "coordinates": [-42.8, -5.1]},
            }
        ],
    }
    try:
        response = TestClient(app).post(
            "/api/v1/import/geojson", headers={"X-API-Key": "change-me"}, json=payload
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 201
    assert response.json()["importados"] == 1
    assert db.committed


def test_mapa_disponivel() -> None:
    response = TestClient(app).get("/map")
    assert response.status_code == 200
    assert "leaflet" in response.text.lower()
