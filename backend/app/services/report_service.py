"""
AI 报告生成服务（M7 模块）
生成专业的财报分析报告，支持 Markdown 格式和 PDF 导出
"""
import logging
import os
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.document import Document, Chunk, FinancialMetric
from app.services.llm_service import generate_sync, FINANCIAL_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

# 报告章节结构
REPORT_SECTIONS = [
    ("一、核心指标速览", "提取并汇总以下核心指标：营收、净利润、毛利率、净利率、ROE、资产负债率。用简洁的表格呈现，标注同比变化。"),
    ("二、收入分析", "分析收入结构（按产品线/业务板块/区域分布），计算各部分的占比和同比变化，识别主要增长驱动力。"),
    ("三、成本与费用分析", "分析营业成本、销售费用、管理费用、研发费用的变化趋势，计算各项费用率（费用/营收），评估费用控制效率。"),
    ("四、资产负债分析", "分析资产负债结构：流动比率、速动比率、资产负债率，评估短期偿债能力和长期财务风险。"),
    ("五、现金流分析", "分析经营活动、投资活动、筹资活动产生的现金流量净额，评估现金流健康度和可持续性。"),
    ("六、风险提示", "整理财报中明确披露的经营风险、财务风险、市场风险，结合财务数据异常点进行补充提示。"),
    ("七、总结与展望", "综合以上分析，给出3-5条核心结论和未来展望。"),
]


def generate_report(
    db: Session,
    user_id: int,
    company_code: str,
    fiscal_year: int,
    report_type: str = "annual",
    document_ids: Optional[list] = None,
) -> dict:
    """
    生成完整的财报分析报告
    :param db: 数据库会话
    :param user_id: 用户 ID
    :param company_code: 股票代码
    :param fiscal_year: 财年
    :param report_type: 报告类型 annual/quarterly/comparison
    :param document_ids: 指定使用的文档 ID 列表
    :return: {report_markdown, sections, metadata}
    """
    # 获取目标文档
    if document_ids:
        docs = db.query(Document).filter(
            Document.id.in_(document_ids),
            Document.user_id == user_id,
            Document.is_deleted == 0,
        ).all()
    else:
        docs = db.query(Document).filter(
            Document.company_code == company_code,
            Document.fiscal_year == fiscal_year,
            Document.user_id == user_id,
            Document.is_deleted == 0,
        ).all()

    if not docs:
        return {"error": "未找到相关财报文档，请先上传并解析文档"}

    # 找到已解析完成的文档
    completed_docs = [d for d in docs if d.parse_status == "completed"]
    if not completed_docs:
        return {"error": "相关文档尚未解析完成，请先完成文档解析"}

    doc = completed_docs[0]
    doc_ids = [d.id for d in completed_docs]

    # 获取文档全部内容用于上下文
    chunks = db.query(Chunk).filter(Chunk.document_id.in_(doc_ids)).all()
    full_context = "\n\n".join([c.content for c in chunks]) if chunks else ""

    # 截断上下文（避免超出 token 限制）
    if len(full_context) > 30000:
        full_context = full_context[:30000] + "\n...(内容过长，已截断)"

    # 逐节生成报告
    report_sections = []
    report_md = f"# {doc.company_name or company_code} {fiscal_year}年度财务分析报告\n\n"
    report_md += f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    report_md += f"> 数据来源：{doc.file_name}\n\n---\n\n"

    for section_title, section_prompt in REPORT_SECTIONS:
        prompt = f"""基于以下财报内容，撰写报告的「{section_title}」章节。

{section_prompt}

## 财报内容
{full_context}

请用专业但易懂的语言撰写，数据引用要具体。如内容不足，标注"财报中未充分披露"。
"""

        section_content = generate_sync(
            messages=[
                {"role": "system", "content": FINANCIAL_ANALYSIS_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1000,
        )

        if section_content:
            report_md += f"## {section_title}\n\n{section_content}\n\n---\n\n"
            report_sections.append({"title": section_title, "content": section_content})
        else:
            report_md += f"## {section_title}\n\n> 此节内容生成失败，请检查 API Key 配置。\n\n---\n\n"

    # 保存报告到数据库
    from app.models.settings import Report
    report_record = Report(
        user_id=user_id,
        company_code=company_code,
        company_name=doc.company_name or company_code,
        fiscal_year=fiscal_year,
        report_type=report_type,
        content_md=report_md,
    )
    db.add(report_record)
    db.commit()
    db.refresh(report_record)

    return {
        "report_id": report_record.id,
        "title": f"{doc.company_name or company_code} {fiscal_year}年度财务分析报告",
        "sections": report_sections,
        "markdown": report_md,
        "metadata": {
            "company_code": company_code,
            "company_name": doc.company_name,
            "fiscal_year": fiscal_year,
            "documents_used": [d.file_name for d in completed_docs],
            "generated_at": datetime.now().isoformat(),
        },
    }


def export_report_as_pdf(report_id: int, db: Session) -> Optional[str]:
    """
    将报告导出为 PDF 文件
    :param report_id: 报告 ID
    :param db: 数据库会话
    :return: PDF 文件路径，失败返回 None
    """
    from app.models.settings import Report

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or not report.content_md:
        return None

    # 如果报告已有 PDF 路径，直接返回
    if report.file_path and os.path.exists(report.file_path):
        return report.file_path

    # 生成 PDF（简化版：将 Markdown 写入 PDF）
    try:
        import markdown
        html = markdown.markdown(report.content_md)

        # 使用简单的 HTML → PDF 方式
        pdf_dir = os.path.join(settings.UPLOAD_DIR, "reports")
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, f"report_{report_id}.pdf")

        # 使用 WeasyPrint（如果可用）或简单方式
        try:
            from weasyprint import HTML
            HTML(string=f"<html><body>{html}</body></html>").write_pdf(pdf_path)
        except ImportError:
            # 降级方案：直接写入 HTML
            html_path = pdf_path.replace('.pdf', '.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font-family:'SimSun',sans-serif;max-width:800px;margin:40px auto;line-height:1.8}}
h1,h2{{color:#1e3c72}} table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #ddd;padding:8px}}</style>
</head><body>{html}</body></html>""")
            return html_path

        report.file_path = pdf_path
        db.commit()
        return pdf_path
    except Exception as e:
        logger.error(f"PDF 导出失败: {e}")
        return None
