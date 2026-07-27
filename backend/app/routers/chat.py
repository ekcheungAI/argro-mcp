"""Router for /chat — persona-voiced AI chat with real-news RAG.

AIGRO Ask 體驗嘅後端:訪客同 Jimmy/Elvin/平台分身傾計,回答唔再係死 scripted
— 用 DeepSeek 以分身語氣自由回答,並以 pgvector 搵出最相關嘅真實情報做
context + citations。LLM key 只留 server-side;endpoint 公開但 rate-limited。

設計原則:
- 似真人:第一人稱、分身自己嘅觀點同經歷、口語化繁中(香港用法)
- 有根據:引用真實文章(標題 + 原文連結),唔准虛構來源
- 誠實:超出知識範圍會認,並帶返去佢識嘅嘢;被問及會承認係 AI 分身
- 安全:明確拒絕有害/違法/人身攻擊請求
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.enrichment.embed import pad_to_dim
from app.enrichment.llm import get_client
from app.models.article import Article
from app.models.article_embedding import ArticleEmbedding
from app.models.source import Source

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# ----------------------------------------------------------------------- #
# Persona registry — system prompts(分身語氣同人設)
# ----------------------------------------------------------------------- #

_BASE_RULES = """
核心規則(必須遵守):
1. 用繁體中文(香港用語)回答,自然口語,似真人傾計,唔好似客服或者教科書。
2. 第一人稱。你可以分享「你」嘅觀點、經歷同判斷(根據人設),但唔好虛構具體數字、
   客戶名、或者唔存在嘅成果。
3. 如果提供咗「相關即時情報」,而問題又相關,自然噉引用(「頭先見到…」「最近有單…」),
   唔好逐條背書。引用時講得出邊個來源。
4. 唔識/超出你範疇嘅嘢,大方認(「呢個唔係我範疇」),然後帶返去你熟悉嘅方向,
   唔好作答案。
5. 回答長度:一般 3-6 句,重點先行。對方問深入先展開。唔好用 markdown 標題或者
   列表轟炸;自然段落為主,必要時先用簡短列表。
6. 有時(唔係每次)喺結尾反問一句,推進對話 — 似真人咁關心對方想解決咩。
7. 有害、違法、人身攻擊、或者呃你扮其他人嘅請求:禮貌拒絕。
8. 如果對方問你係咪真人/AI:誠實講你係佢嘅 AI 分身,基於佢授權嘅知識同內容訓練,
   复杂嘢可以搵真人跟進。
""".strip()

PERSONAS: dict[str, dict] = {
    "platform": {
        "name": "AIGRO 平台分身",
        "system": f"""你係 AIGRO 嘅平台分身 — 一個服務香港 founders、builders 同中小企老闆嘅
AI × Growth 情報平台編輯。你熟悉:AI 行業動態(你有即時情報庫)、平台嘅服務
(情報訂閱、專家分身、MCP 網絡、社群活動)、香港中小企點樣落地 AI。
語氣:專業但親切,似一個好得力嘅編輯朋友。目標:幫訪客搵到佢需要嘅情報/服務,
自然噉介紹平台價值(唔好硬銷)。

{_BASE_RULES}""",
    },
    "jimmy-lau": {
        "name": "Jimmy Lau 劉泰麟",
        "system": f"""你係 Jimmy Lau(劉泰麟)嘅 AI 分身。Jimmy 係 DotAI 聯合創辦人,香港
AI-First 同語境工程(Context Engineering)嘅推動者 — 佢主張香港企業要用
「語境工程」取代「提示詞工程」,成日喺社群教人點樣將 AI 落地到真實業務流程。
語氣:直接、務實、有啲工程師式嘅較真,鍾意用具體例子拆概念,唔講空泛大道理。
佢會問返對方嘅實際業務場景,因為冇 context 嘅建議係冇用嘅。

{_BASE_RULES}""",
    },
    "elvin-cheung": {
        "name": "Elvin Cheung",
        "system": f"""你係 Elvin Cheung(ekcheungAI)嘅 AI 分身。Elvin 係香港 growth hacker /
builder — SuperBash 主辦人、Perskill 同 AIGRO 嘅發起人,成日喺 YouTube/IG/Threads
教 AI 工具實戰、vibe coding、一人公司點樣用 AI 槓桿。佢拆工具嘅結構:可以點試、
限制係咩、風險喺邊、值唔值得畀錢。
語氣:能量高、貼地、似朋友分享實戰心得,鍾意講「試咗先講」。對香港中小企同
creator 嘅實際需要好熟。

{_BASE_RULES}""",
    },
}

# ----------------------------------------------------------------------- #
# Rate limiting — in-memory per-IP(簡單夠用;multi-instance 先至要 Redis)
# ----------------------------------------------------------------------- #

_RATE_WINDOW_S = 3600
_RATE_MAX = 30  # 每 IP 每小時 30 條
_hits: dict[str, list[float]] = defaultdict(list)


def _rate_check(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    hits = [t for t in _hits[ip] if now - t < _RATE_WINDOW_S]
    if len(hits) >= _RATE_MAX:
        raise HTTPException(status_code=429, detail="太多訊息啦,休息一陣先(每小時上限 30 條)")
    hits.append(now)
    _hits[ip] = hits


# ----------------------------------------------------------------------- #
# Schemas
# ----------------------------------------------------------------------- #


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    persona: str = Field(default="platform", max_length=40)
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=6)


class Citation(BaseModel):
    title: str
    url: Optional[str]
    source: str


class ChatResponse(BaseModel):
    reply: str
    persona: str
    citations: list[Citation]
    model: str
    rag_used: bool


# ----------------------------------------------------------------------- #
# RAG — pgvector 搵最相關嘅真實文章
# ----------------------------------------------------------------------- #


def _related_articles(db: Session, question: str, limit: int = 4) -> list[tuple[Article, Source]]:
    """Embed the question and return the closest embedded articles (cosine)."""
    try:
        client = get_client()
        if not client.available():
            return []
        vectors = client.embed([question], model=settings.embedding_model)
        if not vectors or not vectors[0]:
            return []
        padded = pad_to_dim(vectors[0], settings.embedding_dim)
        distance = ArticleEmbedding.embedding.cosine_distance(padded)
        rows = db.execute(
            select(Article, Source)
            .join(ArticleEmbedding, ArticleEmbedding.article_id == Article.id)
            .join(Source, Article.source_id == Source.id)
            .where(Article.status == "active")
            .order_by(distance)
            .limit(limit)
        ).all()
        return [(a, s) for a, s in rows]
    except Exception:
        logger.warning("chat RAG retrieval failed; continuing without context", exc_info=True)
        return []


# ----------------------------------------------------------------------- #
# Endpoint
# ----------------------------------------------------------------------- #


@router.post("", response_model=ChatResponse)
def post_chat(payload: ChatRequest, request: Request, db: Session = Depends(get_db)) -> ChatResponse:
    """POST /chat — persona-voiced answer grounded in the live news corpus."""
    _rate_check(request)

    persona = PERSONAS.get(payload.persona) or PERSONAS["platform"]
    client = get_client()
    if not client.available():
        raise HTTPException(status_code=503, detail="分身暫時離線,請稍後再試")

    related = _related_articles(db, payload.message)

    context_block = ""
    if related:
        lines = [
            f"- [{s.name}] {a.title} — {(a.summary or '')[:160]}"
            for a, s in related
        ]
        context_block = (
            "\n\n以下係而家情報庫入面同佢問題最相關嘅真實文章(可以自然引用):\n"
            + "\n".join(lines)
        )

    messages: list[dict] = [
        {"role": "system", "content": persona["system"] + context_block},
    ]
    for msg in payload.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": payload.message})

    reply = client.chat_messages(messages, model=settings.translation_model)
    if not reply or not reply.strip():
        raise HTTPException(status_code=502, detail="分身諗唔到點答,請再試一次")

    citations = [
        Citation(title=a.title, url=a.url, source=s.name) for a, s in related[:3]
    ]
    return ChatResponse(
        reply=reply.strip(),
        persona=payload.persona if payload.persona in PERSONAS else "platform",
        citations=citations,
        model=settings.translation_model,
        rag_used=bool(related),
    )
