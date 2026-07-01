"""
财报分析仪表盘路由（M6 模块）
指标查询、图表数据、跨公司对比
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.settings import Report, SystemSetting
from app.models.session import Session as ChatSession, Message, Feedback
from app.middleware.auth import get_current_user
from app.services.dashboard_service import get_dashboard_data, get_comparison_data

router = APIRouter(prefix="/api/v1/dashboard", tags=["分析仪表盘"])


@router.get("/bigscreen", summary="数据可视化大屏数据")
def get_bigscreen_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取数据可视化大屏所需的全部汇总数据，包含：
    系统运行状态、业务洞察、问答分析、知识库健康度
    """
    from app.models.document import Document, Chunk, FinancialMetric
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # === 系统运行状态 ===
    total_docs = db.query(func.count(Document.id)).filter(
        Document.is_deleted == 0, Document.user_id == current_user.id
    ).scalar() or 0

    completed_docs = db.query(func.count(Document.id)).filter(
        Document.is_deleted == 0, Document.user_id == current_user.id,
        Document.parse_status == "completed"
    ).scalar() or 0

    failed_docs = db.query(func.count(Document.id)).filter(
        Document.is_deleted == 0, Document.user_id == current_user.id,
        Document.parse_status == "failed"
    ).scalar() or 0

    total_chunks = db.query(func.count(Chunk.id)).join(
        Document, Chunk.document_id == Document.id
    ).filter(Document.is_deleted == 0, Document.user_id == current_user.id).scalar() or 0

    # 今日问答量
    today_msgs = db.query(func.count(Message.id)).select_from(Message).join(
        ChatSession, Message.session_id == ChatSession.id
    ).filter(
        ChatSession.user_id == current_user.id,
        Message.created_at >= today,
        Message.role == 'user'
    ).scalar() or 0

    # 总问答量
    total_msgs = db.query(func.count(Message.id)).select_from(Message).join(
        ChatSession, Message.session_id == ChatSession.id
    ).filter(
        ChatSession.user_id == current_user.id,
        Message.role == 'user'
    ).scalar() or 0

    # 报告数量
    report_count = db.query(func.count()).filter(Report.user_id == current_user.id).scalar() or 0

    # 解析成功率
    parse_rate = round(completed_docs / total_docs * 100, 1) if total_docs > 0 else 0

    # 公司数
    companies = db.query(
        Document.company_code, Document.company_name, func.count(Document.id)
    ).filter(
        Document.is_deleted == 0, Document.user_id == current_user.id,
        Document.company_code.isnot(None)
    ).group_by(Document.company_code, Document.company_name).all()

    # === 问答分析 ===
    # 高频问题 Top 5
    top_questions = db.query(Message.content, func.count(Message.id).label('cnt')).select_from(Message).join(
        ChatSession, Message.session_id == ChatSession.id
    ).filter(
        ChatSession.user_id == current_user.id,
        Message.role == 'user'
    ).group_by(Message.content).order_by(func.count(Message.id).desc()).limit(5).all()

    # 满意度（点赞率）
    total_feedback = db.query(func.count(Feedback.id)).filter(
        Feedback.user_id == current_user.id
    ).scalar() or 0
    up_feedback = db.query(func.count(Feedback.id)).filter(
        Feedback.user_id == current_user.id, Feedback.rating == 'up'
    ).scalar() or 0
    satisfaction = round(up_feedback / total_feedback * 100, 1) if total_feedback > 0 else 0

    # === 年度分布 ===
    year_dist = db.query(
        Document.fiscal_year, func.count(Document.id)
    ).filter(
        Document.is_deleted == 0, Document.user_id == current_user.id,
        Document.fiscal_year.isnot(None)
    ).group_by(Document.fiscal_year).order_by(Document.fiscal_year).all()

    # === 报告列表 ===
    recent_reports = db.query(Report).filter(
        Report.user_id == current_user.id
    ).order_by(Report.created_at.desc()).limit(3).all()

    # === 最近问答记录 ===
    recent_messages = db.query(Message, ChatSession.session_title).select_from(Message).join(
        ChatSession, Message.session_id == ChatSession.id
    ).filter(
        ChatSession.user_id == current_user.id,
        Message.role.in_(['user', 'assistant'])
    ).order_by(Message.created_at.desc()).limit(6).all()

    return {
        "code": 0,
        "data": {
            "system_status": {
                "total_documents": total_docs,
                "completed_documents": completed_docs,
                "failed_documents": failed_docs,
                "total_chunks": total_chunks,
                "total_companies": len(companies),
                "parse_success_rate": parse_rate,
                "total_reports": report_count,
            },
            "qa_metrics": {
                "today_questions": today_msgs,
                "total_questions": total_msgs,
                "satisfaction_rate": satisfaction,
                "total_feedback": total_feedback,
                "top_questions": [
                    {"question": q[0][:60] if q[0] else '', "count": q[1]}
                    for q in top_questions
                ],
            },
            "companies": [
                {"code": c[0], "name": c[1] or c[0], "doc_count": c[2]}
                for c in companies
            ],
            "year_distribution": [
                {"year": y, "count": c} for y, c in year_dist
            ],
            "recent_reports": [
                {"id": r.id, "company_name": r.company_name, "fiscal_year": r.fiscal_year}
                for r in recent_reports
            ],
            "recent_activity": [
                {
                    "title": m[1],
                    "role": m[0].role,
                    "content": (m[0].content or '')[:60],
                    "time": m[0].created_at.strftime('%H:%M') if m[0].created_at else '',
                }
                for m in recent_messages
            ],
        },
    }


@router.post("/{doc_id}/ai-charts", summary="AI 智能图表生成（带缓存）")
def generate_ai_charts(
    doc_id: int,
    refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    使用 DeepSeek AI 分析文档内容，智能提取财务数据并生成图表配置
    结果缓存到 dashboard_cache 表，相同文档无需重复分析
    传 refresh=true 可强制重新生成
    """
    from app.models.document import Document, Chunk
    from app.services.llm_service import generate_sync
    import pymysql, json as j

    doc = db.query(Document).filter(
        Document.id == doc_id, Document.user_id == current_user.id,
        Document.is_deleted == 0, Document.parse_status == "completed",
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在或未解析完成")

    cache_key = f"dashboard_chart_{doc_id}"

    # 检查缓存
    if not refresh:
        cached = db.query(SystemSetting).filter(SystemSetting.setting_key == cache_key).first()
        if cached and cached.setting_value:
            try:
                chart_data = j.loads(cached.setting_value)
                chart_data["_cached"] = True
                return {"code": 0, "data": {"document_info": {"file_name": doc.file_name, "company_code": doc.company_code, "fiscal_year": doc.fiscal_year}, **chart_data}}
            except:
                pass  # 缓存损坏，重新生成

    chunks = db.query(Chunk).filter(Chunk.document_id == doc_id).order_by(Chunk.chunk_index).all()
    full_text = "\n\n".join([c.content for c in chunks])

    if len(full_text) > 20000:
        full_text = full_text[:20000]

    prompt = f"""你是一位资深财务分析师。请仔细阅读以下财报内容，提取所有财务数据并设计可视化图表。

## 要求
1. 提取所有能找到的财务指标，包括：营业收入、净利润、毛利率、净利率、ROE、ROA、资产负债率、研发费用及研发费用率、基本每股收益、经营活动现金流、货币资金、应收账款、存货、固定资产等。每个指标必须包含具体数值和单位（亿元/万元/百分比），如有同比变化也要提取
2. 提取资产结构数据（各资产类别的金额和占比）
3. 设计 3-5 个图表，每个图表需包含：
   - 图表标题（要具体，如"比亚迪2024年度核心财务指标"）
   - 图表类型（bar/line/pie/radar/scatter）
   - 为什么选这个图表（一句话理由）
   - 完整的 data 对象（labels 数组 + values 数组，值必须是具体数字）

## JSON 格式（严格返回此格式，不要多余内容）
{{
  "metrics": [
    {{"name":"营业收入","value":7831.5,"unit":"亿元","yoy":29.8}},
    {{"name":"毛利率","value":25.0,"unit":"%","yoy":0.9}}
  ],
  "structure": [
    {{"name":"货币资金","value":1287.6,"unit":"亿元","ratio":13.0}}
  ],
  "charts": [
    {{
      "type":"bar",
      "title":"2024年度核心财务指标对比",
      "reason":"柱状图直观展示各指标的数值差异",
      "data":{{"labels":["营业收入","净利润","研发费用","经营现金流"],"values":[7831.5,412.8,399.4,1697.3],"unit":"亿元"}}
    }}
  ]
}}

## 财报内容
{full_text}"""

    result = generate_sync(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1, max_tokens=4000,
    )

    try:
        # 清理 Markdown 代码块标记
        cleaned = result.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:])
            if cleaned.rstrip().endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
        chart_data = j.loads(cleaned)

        # 写入缓存
        existing = db.query(SystemSetting).filter(SystemSetting.setting_key == cache_key).first()
        if existing:
            existing.setting_value = j.dumps(chart_data, ensure_ascii=False)
        else:
            db.add(SystemSetting(setting_key=cache_key, setting_value=j.dumps(chart_data, ensure_ascii=False), description=f"AI图表缓存|文档#{doc_id}"))
        db.commit()

        chart_data["_cached"] = False
        return {"code": 0, "data": {"document_info": {"file_name": doc.file_name, "company_code": doc.company_code, "fiscal_year": doc.fiscal_year}, **chart_data}}

    except Exception as e:
        chart_data = {"metrics": [], "structure": [], "charts": [], "error": f"数据解析异常: {str(e)}"}
        return {"code": 0, "data": {"document_info": {"file_name": doc.file_name, "company_code": doc.company_code, "fiscal_year": doc.fiscal_year}, **chart_data}}


@router.get("/{doc_id}", summary="获取仪表盘数据")
def get_dashboard(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取指定文档的完整仪表盘数据
    包含：基础指标卡片、趋势数据、结构数据、雷达图数据
    """
    data = get_dashboard_data(db, doc_id, current_user.id)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return {"code": 0, "data": data}


@router.get("/compare", summary="跨公司对比")
def compare_companies(
    company_codes: str,
    fiscal_year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    对比多家公司在特定年份的核心指标
    :param company_codes: 股票代码，逗号分隔，如 "002594,300750"
    :param fiscal_year: 财年
    """
    codes = [c.strip() for c in company_codes.split(",") if c.strip()]
    data = get_comparison_data(db, codes, fiscal_year, current_user.id)
    return {"code": 0, "data": data}


@router.get("/{doc_id}/metrics", summary="获取该文档的财务指标")
def get_metrics(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取指定文档的所有结构化财务指标"""
    from app.models.document import FinancialMetric, Document

    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == current_user.id,
        Document.is_deleted == 0,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    metrics = db.query(FinancialMetric).filter(
        FinancialMetric.document_id == doc_id,
    ).all()

    return {
        "code": 0,
        "data": [
            {
                "id": m.id,
                "metric_name": m.metric_name,
                "metric_value": m.metric_value,
                "metric_unit": m.metric_unit,
                "yoy_change": m.yoy_change,
                "source_page": m.source_page,
            }
            for m in metrics
        ],
    }
