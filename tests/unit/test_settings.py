import json

import pytest

from nova.infrastructure.config import Settings


def test_cors_origins_from_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://example.com, http://localhost:5173")

    assert Settings().cors_origins == ["https://example.com", "http://localhost:5173"]


def test_cors_origins_from_json_env(monkeypatch: pytest.MonkeyPatch) -> None:
    origins = ["https://example.com", "http://localhost:5173"]
    monkeypatch.setenv("CORS_ORIGINS", json.dumps(origins))

    assert Settings().cors_origins == origins
