"""Response schemas for /insights/* endpoints (docs/03-http-api-spec.md §2.4)."""
from datetime import date

from pydantic import BaseModel


class InsightSection(BaseModel):
    section_title: str
    content: str
    articles: list[str]


class InsightResponse(BaseModel):
    id: str
    type: str
    date: date
    lang: str
    title: str
    summary: str
    sections: list[InsightSection]
