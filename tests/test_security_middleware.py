import asyncio

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


def test_configuracao_rejeita_api_key_fraca_em_todos_os_ambientes() -> None:
    for environment in ("development", "staging", "production"):
        with pytest.raises(ValidationError, match="API_KEY segura"):
            Settings(environment=environment, api_key="change-me")


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
            headers={"Content-Type": "application/json", "X-API-Key": Settings().api_key},
        )
    assert response.status_code == 413


def test_autenticacao_acontece_antes_da_validacao_do_json() -> None:
    with TestClient(production_app) as client:
        response = client.post(
            "/api/v1/import/geojson",
            content=b"nao-e-json",
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 401


def test_limite_nao_emite_duas_respostas_quando_app_le_corpo_tarde() -> None:
    sent: list[dict[str, object]] = []

    async def late_reader(scope, receive, send) -> None:  # type: ignore[no-untyped-def]
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await receive()
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = BodyLimitMiddleware(late_reader, max_body_bytes=4)
    messages = iter([{"type": "http.request", "body": b"12345", "more_body": False}])

    async def receive() -> dict[str, object]:
        return next(messages)

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    asyncio.run(middleware({"type": "http", "method": "POST", "headers": []}, receive, send))
    starts = [message for message in sent if message["type"] == "http.response.start"]
    assert [message["status"] for message in starts] == [413]


def test_rate_limit_libera_lock_antes_de_enviar_429() -> None:
    async def scenario() -> None:
        async def app(scope, receive, send) -> None:  # type: ignore[no-untyped-def]
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        limiter = InMemoryRateLimitMiddleware(app, requests_per_minute=1)

        def scope(client: str) -> dict[str, object]:
            return {
                "type": "http",
                "method": "GET",
                "path": "/x",
                "headers": [],
                "client": (client, 1),
            }

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def discard(message: dict[str, object]) -> None:
            return None

        await limiter(scope("a"), receive, discard)
        blocked_started = asyncio.Event()
        release_blocked = asyncio.Event()

        async def blocked_send(message: dict[str, object]) -> None:
            if message["type"] == "http.response.start":
                blocked_started.set()
                await release_blocked.wait()

        blocked = asyncio.create_task(limiter(scope("a"), receive, blocked_send))
        await blocked_started.wait()
        await asyncio.wait_for(limiter(scope("b"), receive, discard), timeout=0.2)
        release_blocked.set()
        await blocked

    asyncio.run(scenario())


def test_rate_limit_remove_buckets_expirados() -> None:
    now = [0.0]

    async def app(scope, receive, send) -> None:  # type: ignore[no-untyped-def]
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    limiter = InMemoryRateLimitMiddleware(app, requests_per_minute=1, clock=lambda: now[0])

    async def invoke(client: str) -> None:
        scope = {"type": "http", "method": "GET", "path": "/x", "client": (client, 1)}

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            return None

        await limiter(scope, receive, send)

    asyncio.run(invoke("antigo"))
    now[0] = 61.0
    asyncio.run(invoke("novo"))
    assert set(limiter._requests) == {"novo"}
