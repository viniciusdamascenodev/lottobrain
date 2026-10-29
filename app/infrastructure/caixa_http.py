"""Transporte restrito ao endpoint público da Mega-Sena."""
from __future__ import annotations

import socket
import ssl
from http.client import HTTPException
import urllib.error
import urllib.request
from datetime import datetime, timezone

from app.application.collect_mega_sena import CollectionError, FetchResponse, MAX_RESPONSE_BYTES

ENDPOINT = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class CaixaMegaSenaHttp:
    def __init__(self, *, timeout: float = 15):
        if not 1 <= timeout <= 30:
            raise ValueError("timeout deve estar entre 1 e 30 segundos")
        self.timeout = timeout
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        )

    def fetch(self, contest: int | None) -> FetchResponse:
        if contest is not None and (type(contest) is not int or contest <= 0):
            raise ValueError("concurso deve ser inteiro positivo")
        url = ENDPOINT if contest is None else f"{ENDPOINT}/{contest}"
        request = urllib.request.Request(url, headers={
            "Accept": "application/json", "User-Agent": "LottoBrain/0.1 (manual collection)",
            "Accept-Encoding": "identity",
        })
        try:
            try:
                response = self._opener.open(request, timeout=self.timeout)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                if response.geturl() != url:
                    raise CollectionError("unexpected_response_url")
                declared = response.headers.get("Content-Length")
                if declared is not None:
                    try:
                        length = int(declared)
                    except ValueError as exc:
                        raise CollectionError("invalid_content_length") from exc
                    if length < 0 or length > MAX_RESPONSE_BYTES:
                        raise CollectionError("response_too_large")
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise CollectionError("response_too_large")
                if declared is not None and len(body) != length:
                    raise CollectionError("truncated_response")
                return FetchResponse(
                    body, url, response.code, response.headers.get("Content-Type", ""),
                    datetime.now(timezone.utc),
                )
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError, HTTPException) as exc:
            raise CollectionError("http.transport_failure") from exc
