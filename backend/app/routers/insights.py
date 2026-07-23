"""Router for /insights/* (docs/03-http-api-spec.md §2.4)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import optional_api_key, parse_date_param
from app.models.daily_insight import DailyInsight
from app.schemas.insights import InsightResponse, InsightSection

router = APIRouter(prefix="/insights", tags=["insights"], dependencies=[Depends(optional_api_key)])


@router.get("/daily", response_model=InsightResponse)
def get_insight_daily(
    type: str = Query(default="daily", pattern="^(daily|weekly)$"),
    date: Optional[str] = Query(default=None),
    lang: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> InsightResponse:
    """GET /insights/daily — daily/weekly insight document (docs/03 §2.4).

    With ``date``: match that (type, date[, lang]) document. Without ``date``:
    latest available (ordered by date desc). ``lang`` filters only when given.
    """
    query = select(DailyInsight).where(DailyInsight.type == type)
    if date:
        query = query.where(DailyInsight.date == parse_date_param(date, param="date"))
    if lang:
        query = query.where(DailyInsight.lang == lang)
    query = query.order_by(DailyInsight.date.desc()).limit(1)

    insight = db.execute(query).scalars().first()
    if insight is None:
        raise HTTPException(status_code=404, detail="Insight not found")

    sections = [InsightSection.model_validate(s) for s in (insight.sections or [])]
    return InsightResponse(
        id=str(insight.id),
        type=insight.type,
        date=insight.date,
        lang=insight.lang,
        title=insight.title,
        summary=insight.summary,
        sections=sections,
    )
