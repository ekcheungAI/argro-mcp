"""Router for /admin/* — API-key-protected management endpoints.

Sources 嘅 live 配置修正(例如壞 feed URL)需要直接改 DB;呢個 endpoint
俾持有 API key 嘅管理員 upsert source 配置,唔使 direct DB access。
寫操作一律要 key(就算 settings.api_key 未設,admin 都拒絕公開)。
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models.source import Source

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    """Admin 寫操作必須有 key(冇得 public)。"""
    if not settings.api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


class SourceUpsert(BaseModel):
    """以 name 做 natural key upsert source 配置。"""

    name: str
    type: Optional[str] = None  # rss | api | scraper | social
    lang: Optional[str] = None
    homepage_url: Optional[str] = None
    feed_url: Optional[str] = None
    priority_weight: Optional[float] = None
    is_active: Optional[bool] = None
    meta: Optional[dict[str, Any]] = None


@router.post("/sources/upsert", dependencies=[Depends(require_api_key)])
def upsert_source(payload: SourceUpsert, db: Session = Depends(get_db)):
    """POST /admin/sources/upsert — 按 name 更新(或建立)source 配置。

    只更新有提供嘅欄位;用嚟修壞 feed URL / 補 meta config / 停启用來源。
    """
    src = db.execute(select(Source).where(Source.name == payload.name)).scalars().first()
    created = False
    if src is None:
        if not (payload.type and payload.lang and payload.homepage_url):
            raise HTTPException(
                status_code=400,
                detail="new source requires type, lang and homepage_url",
            )
        src = Source(
            name=payload.name,
            type=payload.type,
            lang=payload.lang,
            homepage_url=payload.homepage_url,
        )
        db.add(src)
        created = True

    for field in ("type", "lang", "homepage_url", "feed_url", "priority_weight", "is_active", "meta"):
        value = getattr(payload, field)
        if value is not None:
            setattr(src, field, value)

    db.commit()
    db.refresh(src)
    return {
        "id": str(src.id),
        "name": src.name,
        "created": created,
        "feed_url": src.feed_url,
        "is_active": src.is_active,
        "meta": src.meta,
    }
