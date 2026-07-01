"""
AI 报告生成路由（M7 模块）
报告生成、列表查询、详情查看、下载
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.models.user import User
from app.models.settings import Report
from app.middleware.auth import get_current_user
from app.services.report_service import generate_report, export_report_as_pdf
import os

router = APIRouter(prefix="/api/v1/reports", tags=["报告生成"])


@router.post("/generate", summary="生成财务分析报告")
def create_report(
    company_code: str,
    fiscal_year: int,
    report_type: str = "annual",
    document_ids: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    一键生成专业的财务分析报告
    - 报告包含 7 个章节，涵盖核心指标、收入、成本、资产负债、现金流、风险和总结
    - 生成后自动保存到数据库，可在报告列表查看和下载
    """
    doc_ids = None
    if document_ids:
        doc_ids = [int(d.strip()) for d in document_ids.split(",") if d.strip()]

    result = generate_report(
        db, current_user.id, company_code, fiscal_year, report_type, doc_ids
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"code": 0, "data": result, "msg": "报告生成成功"}


@router.get("", summary="获取报告列表")
def list_reports(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户生成的所有报告列表"""
    query = db.query(Report).filter(Report.user_id == current_user.id)
    total = query.count()
    reports = query.order_by(desc(Report.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {
                    "id": r.id,
                    "company_code": r.company_code,
                    "company_name": r.company_name,
                    "fiscal_year": r.fiscal_year,
                    "report_type": r.report_type,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "has_pdf": bool(r.file_path and os.path.exists(r.file_path)),
                }
                for r in reports
            ],
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/{report_id}", summary="查看报告详情")
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取指定报告的完整 Markdown 内容"""
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == current_user.id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    return {
        "code": 0,
        "data": {
            "id": report.id,
            "company_code": report.company_code,
            "company_name": report.company_name,
            "fiscal_year": report.fiscal_year,
            "report_type": report.report_type,
            "content_md": report.content_md,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        },
    }


@router.get("/{report_id}/download", summary="下载报告 PDF")
def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载指定报告的 PDF 文件"""
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == current_user.id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    pdf_path = export_report_as_pdf(report_id, db)
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF 文件生成失败或不存在")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"财务分析报告_{report.company_name}_{report.fiscal_year}.pdf",
    )


@router.post("/batch-export", summary="批量导出报告")
def batch_export_reports(
    report_ids: list[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量导出多个报告为 ZIP 压缩包
    """
    import zipfile, io, tempfile

    # 生成所有报告的 PDF 或使用现有文件
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for rid in report_ids:
            report = db.query(Report).filter(
                Report.id == rid, Report.user_id == current_user.id
            ).first()
            if not report:
                continue

            # 生成或获取 PDF
            pdf_path = export_report_as_pdf(rid, db)
            if pdf_path and os.path.exists(pdf_path):
                arcname = f"{report.company_name}_{report.fiscal_year}_分析报告.pdf"
                zf.write(pdf_path, arcname)
            elif report.content_md:
                # 没有 PDF 就用 Markdown 文本
                arcname = f"{report.company_name}_{report.fiscal_year}_分析报告.md"
                zf.writestr(arcname, report.content_md.encode('utf-8'))

    zip_buffer.seek(0)
    return FileResponse(
        zip_buffer,
        media_type="application/zip",
        filename="财务分析报告_批量导出.zip",
    )


@router.delete("/{report_id}", summary="删除报告")
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除指定报告"""
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == current_user.id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    # 同时删除 PDF 文件
    if report.file_path and os.path.exists(report.file_path):
        os.remove(report.file_path)

    db.delete(report)
    db.commit()
    return {"code": 0, "msg": "报告已删除"}
