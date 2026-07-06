"""
文档解析服务（M1 模块）
PDF 文本提取、表格结构化、章节切分、OCR 兜底
"""
import os
import hashlib
import re
from typing import Optional, Tuple, List
import logging
logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.document import Document, Chunk, FinancialMetric
from app.models.user import User  # 确保 FK 引用表已注册到 SQLAlchemy metadata


def calculate_file_hash(file_path: str) -> str:
    """计算文件的 SHA256 哈希值，用于去重"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def parse_pdf_text(file_path: str) -> Tuple[str, int, float]:
    """
    使用 PyMuPDF 提取 PDF 中的文本内容
    :param file_path: PDF 文件路径
    :return: (提取的文本, 总页数, 文字覆盖率)
    """
    import fitz  # PyMuPDF

    doc = fitz.open(file_path)
    page_count = len(doc)
    full_text_parts = []
    pages_with_text = 0

    for page_num in range(page_count):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            pages_with_text += 1
        full_text_parts.append(f"=== 第 {page_num + 1} 页 ===\n{text}")

    doc.close()

    # 文字覆盖率 = 有文字的页数 / 总页数
    text_coverage = pages_with_text / page_count if page_count > 0 else 0
    full_text = "\n\n".join(full_text_parts)
    return full_text, page_count, text_coverage


def extract_tables_with_camelot(file_path: str) -> List[dict]:
    """
    使用 Camelot 提取 PDF 中的表格
    :param file_path: PDF 文件路径
    :return: 表格列表，每个表格包含 {page, data(二维列表), accuracy}
    """
    import camelot

    tables = []
    try:
        # lattice 模式：适用于有边框的表格（财报表格通常有边框）
        extracted = camelot.read_pdf(file_path, pages="all", flavor="lattice")
        for i, table in enumerate(extracted):
            tables.append({
                "index": i + 1,
                "page": table.page,
                "data": table.df.values.tolist(),  # 转为二维列表
                "accuracy": float(table.parsing_report["accuracy"]),
            })
    except Exception as e:
        logger.warning(f"Camelot lattice 模式解析失败: {e}")

        # 降级为 stream 模式（适用于无边框表格）
        try:
            extracted = camelot.read_pdf(file_path, pages="all", flavor="stream")
            for i, table in enumerate(extracted):
                tables.append({
                    "index": i + 1,
                    "page": table.page,
                    "data": table.df.values.tolist(),
                    "accuracy": float(table.parsing_report["accuracy"]),
                })
        except Exception as e2:
            logger.warning(f"Camelot stream 模式也解析失败: {e2}")

    return tables


def segment_chapters(full_text: str) -> List[dict]:
    """
    按财报标准章节切分文本
    财报通常包含：管理层讨论与分析、财务报表、报表附注、风险提示等章节
    :param full_text: 完整文本
    :return: 章节列表 [{title, content, start_page}]
    """
    # 财报常见章节标题模式
    chapter_patterns = [
        (r"(第[一二三四五六七八九十\d]+节[^\n]*)", "章节"),
        (r"(管理层讨论与分析)", "管理层讨论与分析"),
        (r"(财务(?:会计)?报表)", "财务报表"),
        (r"((?:合并)?资产负债(?:表|负债表))", "资产负债表"),
        (r"((?:合并)?利润表)", "利润表"),
        (r"((?:合并)?现金流量表)", "现金流量表"),
        (r"((?:合并)?所有者权益变动表)", "所有者权益变动表"),
        (r"(报表附注|财务报表附注)", "报表附注"),
        (r"(关联交易)", "关联交易"),
        (r"(风险[因素提].*)", "风险提示"),
        (r"(公司简介|公司基本情况)", "公司简介"),
        (r"(董事会报告|经营情况讨论与分析)", "董事会报告"),
    ]

    chapters = []
    lines = full_text.split("\n")

    # 查找章节边界
    current_chapter = {"title": "正文", "content": [], "start_page": 1}
    current_page = 1

    for line in lines:
        # 检测页码标记
        page_match = re.match(r"=== 第 (\d+) 页 ===", line)
        if page_match:
            current_page = int(page_match.group(1))
            # 如果当前章节有内容，保存并开始新章节
            if len(current_chapter["content"]) > 20:
                chapters.append({
                    "title": current_chapter["title"],
                    "content": "\n".join(current_chapter["content"]),
                    "start_page": current_chapter["start_page"],
                })
                current_chapter = {"title": "正文（续）", "content": [], "start_page": current_page}
            continue

        # 检测章节标题
        is_new_chapter = False
        for pattern, title in chapter_patterns:
            if re.search(pattern, line):
                if len(current_chapter["content"]) > 20:
                    chapters.append({
                        "title": current_chapter["title"],
                        "content": "\n".join(current_chapter["content"]),
                        "start_page": current_chapter["start_page"],
                    })
                current_chapter = {"title": title, "content": [line], "start_page": current_page}
                is_new_chapter = True
                break
        if not is_new_chapter:
            current_chapter["content"].append(line)

    # 保存最后一个章节
    if current_chapter["content"]:
        chapters.append({
            "title": current_chapter["title"],
            "content": "\n".join(current_chapter["content"]),
            "start_page": current_chapter["start_page"],
        })

    return chapters


def parse_document(db: Session, document_id: int) -> dict:
    """
    完整的文档解析流程：
    1. 文本提取 2. 表格提取 3. 章节切分 4. 结构化存储
    :param db: 数据库会话
    :param document_id: 文档 ID
    :return: 解析结果统计
    """
    # 查询文档记录
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return {"error": "文档不存在"}

    # 先保存文件名到局部变量，避免异常处理时 session 已 rollback 无法访问
    file_name = doc.file_name

    try:
        # 更新状态为解析中
        doc.parse_status = "parsing"
        db.commit()

        file_path = doc.file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # Step 1: 文本提取
        logger.info(f"[解析] 开始提取文本: {file_name}")
        full_text, page_count, text_coverage = parse_pdf_text(file_path)
        doc.page_count = page_count

        # 如果文字覆盖率过低（< 80%），可能是扫描件，需要 OCR
        if text_coverage < 0.8:
            logger.warning(f"[解析] 文字覆盖率仅 {text_coverage:.1%}，确认为扫描件，暂跳过 OCR")
            # TODO: 集成 PaddleOCR 处理扫描件

        # Step 2: 表格提取
        logger.info(f"[解析] 开始提取表格: {doc.file_name}")
        tables = extract_tables_with_camelot(file_path)

        # Step 3: 章节切分
        logger.info(f"[解析] 开始章节切分: {doc.file_name}")
        chapters = segment_chapters(full_text)

        # Step 4: 存储章节文本 Chunk
        chunk_count = 0
        for i, chap in enumerate(chapters):
            if len(chap["content"].strip()) < 50:  # 跳过过短的章节
                continue
            chunk = Chunk(
                document_id=doc.id,
                chunk_index=i + 1,
                chunk_type="text",
                section_title=chap["title"],
                content=chap["content"],
                content_hash=hashlib.md5(chap["content"].encode()).hexdigest(),
                page_start=chap["start_page"],
            )
            db.add(chunk)
            chunk_count += 1

        # Step 5: 存储表格 Chunk
        for table in tables:
            # 将二维表格数据转为 Markdown 表格文本
            md_table = format_table_as_markdown(table["data"])
            chunk = Chunk(
                document_id=doc.id,
                chunk_index=chunk_count + 1,
                chunk_type="table",
                section_title=f"表格 {table['index']}",
                content=md_table,
                page_start=table["page"],
            )
            db.add(chunk)
            chunk_count += 1

        # 更新文档状态
        doc.parse_status = "completed"
        doc.chunk_count = chunk_count
        db.commit()

        # 解析完成后更新 BM25 索引（新增 chunk 加入检索）
        try:
            from app.services.search_service import rebuild_bm25_from_db
            rebuild_bm25_from_db(db)
            logger.info(f"[解析] 已更新 BM25 索引")
        except Exception as e:
            logger.warning(f"[解析] BM25 索引更新失败（不影响解析结果）: {e}")

        return {
            "status": "completed",
            "file_name": doc.file_name,
            "page_count": page_count,
            "text_coverage": round(text_coverage, 2),
            "tables_extracted": len(tables),
            "chapters_found": len(chapters),
            "chunks_created": chunk_count,
        }

    except Exception as e:
        import traceback, datetime
        full_tb = traceback.format_exc()
        logger.error(f"[解析] 文档 {file_name} 解析失败: {e}\n{full_tb}")
        # 写错误日志到文件方便排查
        try:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "parse_errors.log"), "a", encoding="utf-8") as lf:
                lf.write(f"\n{'='*60}\n[{datetime.datetime.now()}] ID={document_id} 文件={file_name}\n{e}\n{full_tb}\n")
        except Exception:
            pass
        db.rollback()  # 先回滚失效的 session
        # 重新查询 doc 再设置失败状态
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.parse_status = "failed"
                db.commit()
        except Exception:
            db.rollback()
        return {"status": "failed", "error": str(e)}


def format_table_as_markdown(data: List[list]) -> str:
    """将二维表格数据转为 Markdown 表格格式"""
    if not data or not data[0]:
        return ""

    lines = []
    # 表头
    header = data[0]
    lines.append("| " + " | ".join(str(c) for c in header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    # 数据行
    for row in data[1:]:
        # 填充不足的列
        padded = list(row) + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(str(c)[:200] for c in padded[:len(header)]) + " |")

    return "\n".join(lines)
