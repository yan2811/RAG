"""
多步推理 Agent 路由（M5 模块）
复杂问题的自动拆解与多步推理
"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.middleware.auth import get_current_user
from app.services.agent_service import execute_agent_reasoning

router = APIRouter(prefix="/api/v1/agent", tags=["多步推理Agent"])


@router.post("/analyze", summary="多步推理分析")
def agent_analyze(
    question: str,
    document_ids: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    对复杂财务问题进行多步推理分析
    系统自动将问题拆解为子问题，逐步检索分析后综合给出报告

    适用场景：
    - 分析某公司近X年盈利能力变化及驱动因素
    - 对比多家公司的财务健康状况
    - 综合评估某公司的投资价值与风险
    """
    doc_ids = None
    if document_ids:
        try:
            doc_ids = [int(d.strip()) for d in document_ids.split(",") if d.strip()]
        except ValueError:
            pass

    result = execute_agent_reasoning(db, question, doc_ids)
    return {"code": 0, "data": result}
