"""Controles ASGI locais para payload e limitação de requisições.

O rate limiter é adequado à demonstração em processo único. Um deploy com
múltiplas réplicas deve substituí-lo por estado compartilhado no gateway/Redis.
"""

from __future__ import annotations

import asyncio
import math
import time
from collections import defaultdict, deque
from collections.abc import Callable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class PayloadTooLargeError(Exception):
    """Sinal interno emitido quando os bytes efetivamente recebidos excedem o limite."""


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        if max_body_bytes < 1:
            raise ValueError("max_body_bytes deve ser positivo")
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                await self._reject(scope, receive, send)
                return
            if declared_size > self.max_body_bytes:
                await self._reject(scope, receive, send)
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise PayloadTooLargeError
            return message

        try:
            await self.app(scope, limited_receive, send)
        except PayloadTooLargeError:
            await self._reject(scope, receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            {"detail": f"payload excede o limite de {self.max_body_bytes} bytes"},
            status_code=413,
            headers={"Connection": "close"},
        )
        await response(scope, receive, send)


class InMemoryRateLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int,
        excluded_paths: set[str] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if requests_per_minute < 1:
            raise ValueError("requests_per_minute deve ser positivo")
        self.app = app
        self.limit = requests_per_minute
        self.window_seconds = 60.0
        self.excluded_paths = excluded_paths or set()
        self.clock = clock
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in self.excluded_paths:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_id = client[0] if client else "desconhecido"
        now = self.clock()
        async with self._lock:
            bucket = self._requests[client_id]
            threshold = now - self.window_seconds
            while bucket and bucket[0] <= threshold:
                bucket.popleft()
            if len(bucket) >= self.limit:
                retry_after = max(1, math.ceil(self.window_seconds - (now - bucket[0])))
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
            bucket.append(now)
            remaining = self.limit - len(bucket)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-ratelimit-limit", str(self.limit).encode()),
                        (b"x-ratelimit-remaining", str(remaining).encode()),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)
