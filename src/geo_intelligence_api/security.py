"""Controles ASGI locais para autenticação, payload e limitação de requisições.

O rate limiter é adequado à demonstração em processo único. Um deploy com
múltiplas réplicas deve substituí-lo por estado compartilhado no gateway/Redis.
"""

from __future__ import annotations

import asyncio
import math
import secrets
import time
from collections import deque
from collections.abc import Callable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

Clock = Callable[[], float]


class BodyLimitMiddleware:
    """Rejeita corpos acima do limite antes de iniciar a aplicação downstream."""

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        if max_body_bytes <= 0:
            raise ValueError("max_body_bytes deve ser positivo")
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = self._content_length(scope)
        if content_length is not None and content_length > self.max_body_bytes:
            await self._reject(scope, receive, send)
            return

        messages: list[Message] = []
        received = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break
            received += len(message.get("body", b""))
            if received > self.max_body_bytes:
                await self._reject(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        position = 0

        async def replay_receive() -> Message:
            nonlocal position
            if position < len(messages):
                message = messages[position]
                position += 1
                return message
            return await receive()

        await self.app(scope, replay_receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            {"detail": f"payload excede o limite de {self.max_body_bytes} bytes"},
            status_code=413,
            headers={"Connection": "close"},
        )
        await response(scope, receive, send)

    @staticmethod
    def _content_length(scope: Scope) -> int | None:
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    return int(value)
                except ValueError:
                    return None
        return None


class ImportAPIKeyMiddleware:
    """Autentica a rota de importação antes de qualquer parsing do corpo."""

    def __init__(
        self,
        app: ASGIApp,
        api_key: str,
        protected_path: str = "/api/v1/import/geojson",
    ) -> None:
        self.app = app
        self.api_key = api_key
        self.protected_path = protected_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        protected = (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and scope.get("path") == self.protected_path
        )
        if protected:
            supplied = next(
                (
                    value.decode("utf-8", errors="replace")
                    for name, value in scope.get("headers", [])
                    if name.lower() == b"x-api-key"
                ),
                "",
            )
            if not secrets.compare_digest(supplied, self.api_key):
                response = JSONResponse(
                    {"detail": "API key inválida"},
                    status_code=401,
                    headers={"WWW-Authenticate": "ApiKey"},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


class InMemoryRateLimitMiddleware:
    """Janela deslizante local por endereço visto diretamente pelo servidor ASGI."""

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int,
        excluded_paths: set[str] | None = None,
        clock: Clock = time.monotonic,
    ) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute deve ser positivo")
        self.app = app
        self.limit = requests_per_minute
        self.window_seconds = 60.0
        self.excluded_paths = excluded_paths or set()
        self._requests: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()
        self._clock = clock
        self._last_cleanup = clock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in self.excluded_paths:
            await self.app(scope, receive, send)
            return

        now = self._clock()
        client = scope.get("client")
        identity = str(client[0]) if client else "desconhecido"
        retry_after: int | None = None
        remaining = 0

        async with self._lock:
            if now - self._last_cleanup >= self.window_seconds:
                self._remove_expired_buckets(now)
                self._last_cleanup = now
            bucket = self._requests.setdefault(identity, deque())
            threshold = now - self.window_seconds
            while bucket and bucket[0] <= threshold:
                bucket.popleft()
            if len(bucket) >= self.limit:
                retry_after = max(1, math.ceil(self.window_seconds - (now - bucket[0])))
            else:
                bucket.append(now)
                remaining = self.limit - len(bucket)

        if retry_after is not None:
            response = JSONResponse(
                {"detail": "limite de requisições excedido"},
                status_code=429,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                },
            )
            await response(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-ratelimit-limit", str(self.limit).encode()),
                        (b"x-ratelimit-remaining", str(remaining).encode()),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)

    def _remove_expired_buckets(self, now: float) -> None:
        threshold = now - self.window_seconds
        expired = [
            identity
            for identity, bucket in self._requests.items()
            if not bucket or bucket[-1] <= threshold
        ]
        for identity in expired:
            del self._requests[identity]
