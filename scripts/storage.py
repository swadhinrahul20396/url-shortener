"""Thread-safe in-memory store for short-code -> link mappings.

A single dict + lock is sufficient for a single-process demo service. The
public methods form a narrow interface (create/get/delete/increment/exists)
so this class can be swapped for a Redis- or DynamoDB-backed store later
without touching the FastAPI routes.
"""
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class LinkRecord:
    code: str
    long_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    clicks: int = 0
    last_accessed_at: Optional[datetime] = None


class InMemoryStore:
    def __init__(self) -> None:
        self._records: Dict[str, LinkRecord] = {}
        self._lock = threading.Lock()

    def exists(self, code: str) -> bool:
        with self._lock:
            return code in self._records

    def create(self, code: str, long_url: str, ttl_seconds: Optional[int]) -> LinkRecord:
        now = datetime.now(timezone.utc)
        expires_at = None
        if ttl_seconds is not None:
            expires_at = datetime.fromtimestamp(now.timestamp() + ttl_seconds, tz=timezone.utc)
        record = LinkRecord(code=code, long_url=long_url, created_at=now, expires_at=expires_at)
        with self._lock:
            if code in self._records:
                raise KeyError(f"code '{code}' already exists")
            self._records[code] = record
        return record

    def get(self, code: str) -> Optional[LinkRecord]:
        with self._lock:
            record = self._records.get(code)
            if record is None:
                return None
            if record.expires_at is not None and record.expires_at < datetime.now(timezone.utc):
                del self._records[code]
                return None
            return record

    def increment_clicks(self, code: str) -> None:
        with self._lock:
            record = self._records.get(code)
            if record is not None:
                record.clicks += 1
                record.last_accessed_at = datetime.now(timezone.utc)

    def delete(self, code: str) -> bool:
        with self._lock:
            return self._records.pop(code, None) is not None
