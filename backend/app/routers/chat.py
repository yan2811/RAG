"""
智能问答路由（M4 + M8 模块）
SSE 流式问答、会话管理、对话历史、导出
"""
import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.session import Session as ChatSession, Message, Feedback
from app.middleware.auth import get_current_user
from app.services.llm_service import (
    get_system_prompt, rewrite_query, stream_generate,
    post_process_answer, analyze_question_type,
)
from app.services.search_service import hybrid_search
from app.services.embedding_service import embed_query

router = APIRouter(prefix="/api/v1", tags=["智能问答"])


# ============================================================
# 会话管理（M8）
# ============================================================

@router.get("/sessions", summary="获取会话列表")
def list_sessions(
    page: int = 1,
    page_size: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的会话列表，按更新时间倒序"""
    query = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id,
        ChatSession.status == "active",
    )
    total = query.count()
    sessions = query.order_by(desc(ChatSession.updated_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = [
        {
            "id": s.id,
            "session_title": s.session_title,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            "message_count": db.query(func.count(Message.id)).filter(
                Message.session_id == s.id
            ).scalar() or 0,
        }
        for s in sessions
    ]

    return {"code": 0, "data": {"total": total, "items": items, "page": page, "page_size": page_size}}


@router.post("/sessions", summary="创建新会话")
def create_session(
    title: Optional[str] = "新对话",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建一个新的对话会话"""
    session = ChatSession(user_id=current_user.id, session_title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"code": 0, "data": {"id": session.id, "session_title": session.session_title}}


@router.put("/sessions/{session_id}", summary="更新会话标题")
def update_session(
    session_id: int,
    title: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重命名会话"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    session.session_title = title
    db.commit()
    return {"code": 0, "msg": "会话已更新"}


@router.delete("/sessions/{session_id}", summary="删除会话")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除会话及其所有消息"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    session.status = "archived"
    db.commit()
    return {"code": 0, "msg": "会话已删除"}


@router.get("/sessions/{session_id}/messages", summary="获取会话消息历史")
def get_messages(
    session_id: int,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取指定会话的所有消息记录"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = db.query(Message).filter(
        Message.session_id == session_id,
    ).order_by(Message.created_at).offset((page - 1) * page_size).limit(page_size).all()

    items = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": m.sources,
            "token_usage": m.token_usage,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]

    return {"code": 0, "data": {"total": len(items), "items": items}}


@router.get("/sessions/{session_id}/export", summary="导出会话为 Markdown")
def export_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将会话内容导出为 Markdown 格式"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = db.query(Message).filter(
        Message.session_id == session_id,
    ).order_by(Message.created_at).all()

    md_lines = [
        f"# {session.session_title}",
        f"",
        f"> 导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        "---",
        "",
    ]

    for m in messages:
        role_label = "**用户**" if m.role == "user" else "**🤖 财报RAG助手**"
        md_lines.append(f"### {role_label}")
        md_lines.append(m.content)
        if m.sources:
            md_lines.append("")
            md_lines.append("> **数据来源：**")
            for src in m.sources:
                md_lines.append(f"> - {src.get('doc_name', '未知')} · {src.get('section', '')} (第{src.get('page', '?')}页)")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    markdown = "\n".join(md_lines)
    return {"code": 0, "data": {"markdown": markdown, "session_title": session.session_title}}


# ============================================================
# 智能问答（M4 核心）
# ============================================================

def build_chat_context(
    db: Session,
    session_id: int,
    question: str,
    document_ids: Optional[List[int]] = None,
) -> tuple:
    """
    构建问答上下文：
    - 有选择文档 → RAG 模式：混合检索 + 文档上下文
    - 未选文档 → 纯 AI 模式：直接使用 LLM 知识回答
    :return: (messages列表, 检索来源列表, 是否使用RAG)
    """
    # 获取对话历史（最近 10 条消息，即 5 轮）
    history = db.query(Message).filter(
        Message.session_id == session_id,
    ).order_by(desc(Message.created_at)).limit(10).all()
    history = list(reversed(history))

    history_messages = []
    for m in history:
        history_messages.append({"role": m.role, "content": m.content})

    # 判断是否使用 RAG 模式
    use_rag = bool(document_ids and len(document_ids) > 0)
    sources = []

    if use_rag:
        # RAG 模式：查询改写 + 混合检索 + 文档上下文
        rewritten = rewrite_query(question)

        search_results = hybrid_search(
            query=rewritten,
            top_k=5,
            filter_doc_ids=document_ids,
            vector_weight=0.6,
        )

        context_parts = []
        for i, r in enumerate(search_results):
            meta = r.get("metadata", {})
            source_info = {
                "index": i + 1,
                "doc_name": f"文档 #{meta.get('document_id', '?')}",
                "section": meta.get("section_title", "未知章节"),
                "page": meta.get("page_start", "?"),
                "chunk_type": meta.get("chunk_type", "text"),
            }
            sources.append(source_info)
            context_parts.append(
                f"[来源{i + 1}] 章节：{source_info['section']} "
                f"第{source_info['page']}页\n{r['text']}"
            )

        context_text = "\n\n---\n\n".join(context_parts) if context_parts else "未找到相关财报内容。"
        system_prompt = get_system_prompt()
        system_prompt += (
            "\n\n## 检索到的财报内容（来自用户选择的知识库文档）\n"
            "请优先使用以下内容回答。如果用户问的指标（如毛利率、净利率、增长率等）没有直接出现，"
            "但你能从内容中找到计算所需的原始数据（如营收、成本、净利润等），请自己计算并回答。\n\n"
            f"{context_text}\n\n"
            "回答要求：\n"
            "1. 有直接数据→引用并标注[来源X]\n"
            "2. 需要计算→说明计算过程并给出结果\n"
            "3. 确实没有→诚实说明"
        )
    else:
        # 纯 AI 模式：使用通用知识回答财务问题
        system_prompt = get_system_prompt()
        system_prompt += "\n\n## 注意\n当前未选择任何知识库文档，请基于你的财务专业知识回答用户的问题。"
        system_prompt += "你可以引用公开的财务知识和行业常识，但如果涉及具体公司的最新数据，请提醒用户上传相关财报以获得更准确的答案。"

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history_messages[:-1] if len(history_messages) > 1 else [])
    messages.append({"role": "user", "content": question})

    return messages, sources, use_rag


@router.post("/chat/{session_id}", summary="发送消息（SSE 流式回答）")
async def chat(
    session_id: int,
    question: str,
    document_ids: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    向指定会话发送问题，返回 SSE 流式回答
    事件类型：thinking / sources / answer / done
    """
    # 验证会话归属
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 解析文档 ID 列表
    doc_ids = None
    if document_ids:
        try:
            doc_ids = [int(d.strip()) for d in document_ids.split(",") if d.strip()]
        except ValueError:
            pass

    # 保存用户消息
    user_msg = Message(
        session_id=session_id,
        role="user",
        content=question,
    )
    db.add(user_msg)
    db.commit()

    # 构建上下文
    messages, sources, use_rag = build_chat_context(db, session_id, question, doc_ids)

    async def event_generator():
        """SSE 事件流生成器"""
        # 事件 1：发送模式信息和来源
        mode_info = "RAG检索增强" if use_rag else "AI直接回答（未选择文档时基于通用知识）"
        yield f"data: {json.dumps({'type': 'mode', 'mode': 'rag' if use_rag else 'ai', 'info': mode_info, 'sources': sources}, ensure_ascii=False)}\n\n"

        # 事件 2：流式生成答案
        answer_parts = []
        for chunk in stream_generate(messages):
            answer_parts.append(chunk)
            # 按句子拆分发送，减少 SSE 事件频率
            yield f"data: {json.dumps({'type': 'answer', 'content': chunk}, ensure_ascii=False)}\n\n"

        # 拼接完整答案
        full_answer = "".join(answer_parts)

        # 后处理
        full_answer = post_process_answer(full_answer, sources)

        # 保存助手消息
        assistant_msg = Message(
            session_id=session_id,
            role="assistant",
            content=full_answer,
            sources=sources,
            token_usage={"model": "deepseek-chat"},
        )
        db.add(assistant_msg)
        db.commit()

        # 事件 3：完成
        yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg.id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# 消息反馈（M8）
# ============================================================

@router.post("/chat/{session_id}/feedback", summary="对消息进行反馈")
def submit_feedback(
    session_id: int,
    message_id: int,
    rating: str,  # "up" 或 "down"
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户对 AI 回答进行点赞或点踩"""
    if rating not in ("up", "down"):
        raise HTTPException(status_code=400, detail="rating 必须为 up 或 down")

    # 检查是否已评价
    existing = db.query(Feedback).filter(
        Feedback.message_id == message_id,
        Feedback.user_id == current_user.id,
    ).first()

    if existing:
        existing.rating = rating
        existing.reason = reason
    else:
        feedback = Feedback(
            message_id=message_id,
            user_id=current_user.id,
            rating=rating,
            reason=reason,
        )
        db.add(feedback)

    db.commit()
    return {"code": 0, "msg": "反馈已提交"}
