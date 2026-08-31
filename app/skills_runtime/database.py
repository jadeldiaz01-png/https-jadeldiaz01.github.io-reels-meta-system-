from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_engine_from_env() -> AsyncEngine:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("database_url_unavailable")
    return create_async_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
