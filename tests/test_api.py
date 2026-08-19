from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from geo_intelligence_api.config import get_settings
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

    def first(self) -> Any | None:
        return self._rows[0] if self._rows else None


class FakeDB:
    def __init__(self, rows: list[Any] | None = None) -> None:
        self.rows = rows or []
        self.committed = False
        self.rolled_back = False
        self.queries: list[str] = []
        self.batches: dict[str, Any] = {}

    def execute(self, statement: Any, params: Any = None, **_kwargs: Any) -> Result:
        self.queries.append(str(statement))
        if "dataset_batches" in str(statement) and params:
            batch = self.batches.get(params.get("content_sha256", ""))
            return Result([batch] if batch else [])
        return Result(self.rows)

    def add(self, item: Any) -> None:
        if item.__class__.__name__ == "DatasetBatch":
            self.batches[item.content_sha256] = item

    def flush(self) -> None:
        pass

    def add_all(self, _items: list[Any]) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class ConcurrentDB(FakeDB):
    def flush(self) -> None:
        raise IntegrityError("insert dataset_batches", {}, Exception("unique violation"))


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
    db = FakeDB(
        [
            {
                "id": 1,
                "nome": "UBS Teste",
                "tipo": "saude",
                "fonte": "teste",
                "lon": -42.8,
                "lat": -5.1,
            }
        ]
    )
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).get(
            "/api/v1/coverage?lat=-5.09&lon=-42.8&raio_m=1000&tipo=saude"
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["type"] == "FeatureCollection"
    assert response.json()["summary"]["total"] == 1
    assert response.json()["features"][0]["properties"]["nome"] == "UBS Teste"
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
            "/api/v1/import/geojson",
            headers={"X-API-Key": get_settings().api_key},
            json=payload,
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 201
    assert response.json()["importados"] == 1
    assert db.committed


def test_reimportacao_do_mesmo_dataset_e_idempotente() -> None:
    db = FakeDB()
    app.dependency_overrides[get_db] = lambda: db
    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "source": "OpenStreetMap contributors",
            "license": "ODbL 1.0",
            "version": "2026-08-19T13:37:17Z",
        },
        "features": [
            {
                "type": "Feature",
                "properties": {"nome": "Unidade", "tipo": "saude", "fonte": "OSM"},
                "geometry": {"type": "Point", "coordinates": [-42.8, -5.1]},
            }
        ],
    }
    try:
        first = TestClient(app).post(
            "/api/v1/import/geojson",
            headers={"X-API-Key": get_settings().api_key},
            json=payload,
        )
        second = TestClient(app).post(
            "/api/v1/import/geojson",
            headers={"X-API-Key": get_settings().api_key},
            json=payload,
        )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 201
    assert first.json()["status"] == "importado"
    assert first.json()["importados"] == 1
    assert second.status_code == 200
    assert second.json()["status"] == "ja_importado"
    assert second.json()["importados"] == 0
    assert second.json()["duplicados"] == 1
    assert first.json()["dataset_hash"] == second.json()["dataset_hash"]


def test_importacao_concorrente_retorna_lote_existente() -> None:
    db = ConcurrentDB()
    app.dependency_overrides[get_db] = lambda: db
    payload = {
        "type": "FeatureCollection",
        "metadata": {"source": "OSM", "version": "v1"},
        "features": [
            {
                "type": "Feature",
                "properties": {"nome": "Unidade", "tipo": "saude", "fonte": "OSM"},
                "geometry": {"type": "Point", "coordinates": [-42.8, -5.1]},
            }
        ],
    }
    try:
        response = TestClient(app).post(
            "/api/v1/import/geojson",
            headers={"X-API-Key": get_settings().api_key},
            json=payload,
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ja_importado"
    assert db.rolled_back


def test_lista_lotes_com_proveniencia() -> None:
    db = FakeDB(
        [
            {
                "id": "lote-1",
                "content_sha256": "a" * 64,
                "source": "OpenStreetMap contributors",
                "source_version": "2026-08-19T13:37:17Z",
                "license": "ODbL 1.0",
                "feature_count": 20,
                "imported_at": "2026-08-19T15:00:00Z",
            }
        ]
    )
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).get("/api/v1/datasets")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["source"] == "OpenStreetMap contributors"
    assert response.json()[0]["feature_count"] == 20
    assert "content_sha256" in response.json()[0]


def test_cobertura_por_territorio_retorna_poligono_e_equipamentos() -> None:
    db = FakeDB(
        [
            {
                "code": "2211001",
                "name": "Teresina",
                "source": "IBGE — API de Malhas Geográficas",
                "source_url": "https://servicodados.ibge.gov.br/",
                "license": "Dados públicos do IBGE; citar a fonte",
                "acquired_at": "2026-08-19T16:38:33Z",
                "quality": "mínima; demonstração",
                "geometry": {"type": "MultiPolygon", "coordinates": []},
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [-42.8, -5.09]},
                        "properties": {"id": 1, "nome": "Hospital A", "tipo": "hospital"},
                    }
                ],
            }
        ]
    )
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).get("/api/v1/territories/2211001/coverage")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["territorio"]["codigo"] == "2211001"
    assert body["territorio"]["fonte"].startswith("IBGE")
    assert body["equipamentos"]["type"] == "FeatureCollection"
    assert body["resumo"]["total"] == 1


def test_cobertura_por_territorio_inexistente_retorna_404() -> None:
    app.dependency_overrides[get_db] = lambda: FakeDB([])
    try:
        response = TestClient(app).get("/api/v1/territories/0000000/coverage")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_mapa_disponivel_e_consulta_cobertura() -> None:
    response = TestClient(app).get("/map")
    assert response.status_code == 200
    assert "leaflet" in response.text.lower()
    assert "/api/v1/coverage" in response.text
    assert "Não é cadastro oficial" in response.text
