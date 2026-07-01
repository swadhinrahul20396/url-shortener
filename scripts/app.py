"""FastAPI URL shortener service.

Run directly:
    python app.py                 # serves on http://127.0.0.1:8000

Run with auto-reload for development:
    uvicorn app:app --reload
"""
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from models import ShortenRequest, ShortenResponse, StatsResponse
from shortener import generate_code
from storage import InMemoryStore
from validators import validate_alias, validate_url

app = FastAPI(
    title="URL Shortener",
    description="In-memory URL shortener with SSRF/malicious-URL protection.",
    version="1.0.0",
)
store = InMemoryStore()

BASE_URL = "http://127.0.0.1:8000"


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/shorten", response_model=ShortenResponse, status_code=201)
def shorten(payload: ShortenRequest) -> ShortenResponse:
    try:
        long_url = validate_url(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if payload.custom_alias:
        try:
            code = validate_alias(payload.custom_alias)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if store.exists(code):
            raise HTTPException(status_code=409, detail=f"alias '{code}' is already taken")
    else:
        try:
            code = generate_code(store)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    record = store.create(code, long_url, payload.ttl_seconds)

    return ShortenResponse(
        code=record.code,
        short_url=f"{BASE_URL}/{record.code}",
        long_url=record.long_url,
        created_at=_iso(record.created_at),
        expires_at=_iso(record.expires_at),
    )


@app.get("/api/stats/{code}", response_model=StatsResponse)
def stats(code: str) -> StatsResponse:
    record = store.get(code)
    if record is None:
        raise HTTPException(status_code=404, detail=f"code '{code}' not found")
    return StatsResponse(
        code=record.code,
        long_url=record.long_url,
        created_at=_iso(record.created_at),
        expires_at=_iso(record.expires_at),
        clicks=record.clicks,
        last_accessed_at=_iso(record.last_accessed_at),
    )


@app.delete("/api/{code}", status_code=204)
def delete(code: str) -> None:
    if not store.delete(code):
        raise HTTPException(status_code=404, detail=f"code '{code}' not found")


@app.get("/{code}")
def redirect(code: str) -> RedirectResponse:
    record = store.get(code)
    if record is None:
        raise HTTPException(status_code=404, detail=f"code '{code}' not found")
    store.increment_clicks(code)
    return RedirectResponse(url=record.long_url, status_code=307)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
