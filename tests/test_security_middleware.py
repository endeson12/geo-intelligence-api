import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import ValidationError

from geo_intelligence_api.config import Settings
from geo_intelligence_api.main import app as production_app
from geo_intelligence_api.security import BodyLimitMiddleware, InMemoryRateLimitMiddleware


def _test_app(*, max_body_bytes: int = 16, requests_per_minute: int = 2) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        InMemoryRateLimitMiddleware,
        requests_per_minute=requests_per_minute,
        excluded_paths={"/health/live"},
    )
    app.add_middleware(BodyLimitMiddleware, max_body_bytes=max_body_bytes)

    @app.post("/echo")
    async def echo(request: Request) -> JSONResponse:
        return JSONResponse({"body": (await request.body()).decode()})

    @app.get("/health/live")
    async def health() -> dict[str, str]:
        return {"status": "vivo"}

    return app


def test_limite_rejeita_corpo_real_maior_sem_content_length() -> None:
    with TestClient(_test_app(max_body_bytes=4)) as client:
        response = client.post(
            "/echo",
            content=(chunk for chunk in [b"123", b"45"]),
            headers={"Content-Type": "application/octet-stream"},
        )

    assert response.status_code == 413
    assert response.json()["detail"] == "payload excede o limite de 4 bytes"


def test_limite_rejeita_content_length_antes_de_ler_corpo() -> None:
    with TestClient(_test_app(max_body_bytes=4)) as client:
        response = client.post("/echo", content=b"12345")

    assert response.status_code == 413
    assert response.headers["connection"] == "close"


def test_rate_limit_retorna_429_e_cabecalhos() -> None:
    with TestClient(_test_app(requests_per_minute=2)) as client:
        assert client.get("/echo").status_code == 405
        assert client.get("/echo").status_code == 405
        blocked = client.get("/echo")

    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "limite de requisições excedido"
    assert blocked.headers["retry-after"]
    assert blocked.headers["x-ratelimit-limit"] == "2"
    assert blocked.headers["x-ratelimit-remaining"] == "0"


def test_health_nao_consumido_pelo_rate_limit() -> None:
    with TestClient(_test_app(requests_per_minute=1)) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/live").status_code == 200


def test_configuracao_de_producao_rejeita_api_key_padrao() -> None:
    with pytest.raises(ValidationError, match="API_KEY segura"):
        Settings(environment="production", api_key="change-me")


@pytest.mark.parametrize("field", ["max_body_bytes", "requests_per_minute"])
def test_configuracao_rejeita_limites_nao_positivos(field: str) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: 0})


def test_aplicacao_rejeita_payload_acima_do_limite_configurado() -> None:
    oversized = b"x" * (Settings().max_body_bytes + 1)
    with TestClient(production_app) as client:
        response = client.post(
            "/api/v1/import/geojson",
            content=oversized,
            headers={"Content-Type": "application/json", "X-API-Key": "change-me"},
        )

    assert response.status_code == 413
