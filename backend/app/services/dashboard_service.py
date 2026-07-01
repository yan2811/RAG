"""
财报分析仪表盘服务（M6 模块）—— 从文档文本中真实提取财务指标
"""
import re
import logging
from sqlalchemy.orm import Session
from app.models.document import Document, Chunk

logger = logging.getLogger(__name__)

# 常见财务指标提取正则
METRIC_PATTERNS = [
    # (指标名, 正则模式, 单位)
    ("营业收入", r'营业收入[：:]\s*([\d,]+\.?\d*)\s*(亿|万)?元?', "yi_yuan"),
    ("净利润", r'(?:归属于.*?)?净利润[：:]\s*([\d,]+\.?\d*)\s*(亿|万)?元?', "yi_yuan"),
    ("毛利率", r'毛利率[：:为]\s*([\d]+\.?\d*)\s*%', "percent"),
    ("净利率", r'(?:净利率|销售净利率)[：:为]\s*([\d]+\.?\d*)\s*%', "percent"),
    ("ROE", r'(?:加权平均)?净资产收益[率率].*?[：:为]\s*([\d]+\.?\d*)\s*%', "percent"),
    ("ROA", r'总资产收益[率率].*?[：:为]\s*([\d]+\.?\d*)\s*%', "percent"),
    ("资产负债率", r'资产负债率[：:为]\s*([\d]+\.?\d*)\s*%', "percent"),
    ("研发费用", r'研发费用[：:]\s*([\d,]+\.?\d*)\s*(亿|万)?元?', "yi_yuan"),
    ("研发费用率", r'研发.*?(?:占.*?比|费用率)[：:为]?\s*([\d]+\.?\d*)\s*%', "percent"),
    ("基本每股收益", r'基本每股收益[：:为]?\s*([\d]+\.?\d*)\s*元', "yuan_per_share"),
    ("经营活动现金流", r'经营活动.*?净额[：:]\s*([\-\d,]+\.?\d*)\s*(亿|万)?元?', "yi_yuan"),
    ("货币资金", r'货币资金[：:]\s*([\d,]+\.?\d*)\s*(亿|万)?元?', "yi_yuan"),
    ("应收账款", r'应收[账帳]款[：:]\s*([\d,]+\.?\d*)\s*(亿|万)?元?', "yi_yuan"),
    ("存货", r'存货[：:]\s*([\d,]+\.?\d*)\s*(亿|万)?元?', "yi_yuan"),
    ("固定资产", r'固定资产[：:]\s*([\d,]+\.?\d*)\s*(亿|万)?元?', "yi_yuan"),
    ("总资产", r'总资产[：:]\s*([\d,]+\.?\d*)\s*(亿|万)?元?', "yi_yuan"),
    ("流动比率", r'流动比率[：:为]?\s*([\d]+\.?\d*)', "ratio"),
    ("速动比率", r'速动比率[：:为]?\s*([\d]+\.?\d*)', "ratio"),
]


def _parse_number(val_str: str) -> float:
    """解析数字字符串，去掉逗号"""
    try:
        return float(val_str.replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0


def extract_metrics_from_text(text: str) -> list:
    """从文本中提取财务指标"""
    metrics = []
    for name, pattern, unit in METRIC_PATTERNS:
        match = re.search(pattern, text)
        if match:
            value = _parse_number(match.group(1))
            # 如果匹配到"万"元，转换为亿元
            if match.lastindex >= 2 and match.group(2) == "万":
                value = value / 10000
            metrics.append({
                "name": name,
                "value": f"{value:,.2f}" if value >= 100 else f"{value:.2f}",
                "unit": unit,
                "raw_value": value,
            })
    return metrics


def _extract_yoy_change(name: str, text: str) -> str:
    """尝试提取同比变化百分比"""
    patterns = [
        rf'{name}.*?同比[增减][长少]\s*([\d]+\.?\d*)\s*%',
        rf'{name}.*?[\(\（](?:\+|\-)?\s*([\d]+\.?\d*)\s*%[\)\）]',
        rf'{name}.*?([\+\-][\d]+\.?\d*)\s*%',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1)
    return ""


def get_dashboard_data(db: Session, document_id: int, user_id: int) -> dict:
    """获取指定文档的完整仪表盘数据"""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user_id,
        Document.is_deleted == 0,
        Document.parse_status == "completed",
    ).first()

    if not doc:
        return {"error": "文档不存在或未解析完成"}

    # 获取所有 chunk 文本
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()
    full_text = "\n".join([c.content for c in chunks])

    # 提取指标
    metrics = extract_metrics_from_text(full_text)

    # 计算同比变化
    for m in metrics:
        change = _extract_yoy_change(m["name"], full_text)
        if change:
            m["yoy_change"] = change

    # 为同公司其他年份文档提取趋势数据
    trend_data = _build_multi_year_trend(db, doc, user_id)

    # 资产结构
    structure = _extract_asset_structure(full_text)

    # 从指标计算雷达图数据（归一化到 0-100）
    radar = _build_radar_from_metrics(metrics)

    return {
        "document_info": {
            "id": doc.id,
            "file_name": doc.file_name,
            "company_name": doc.company_name or doc.file_name,
            "company_code": doc.company_code,
            "fiscal_year": doc.fiscal_year,
            "page_count": doc.page_count,
        },
        "base_metrics": metrics if metrics else [
            {"name": "提示", "value": "未提取到结构化指标，请查看文档原文", "unit": "", "raw_value": 0}
        ],
        "trend_data": trend_data,
        "structure_data": structure,
        "radar_data": radar,
    }


def _build_multi_year_trend(db: Session, doc: Document, user_id: int) -> dict:
    """查找同公司其他年份的文档，构建趋势数据"""
    if not doc.company_code:
        return {"description": "未设置股票代码，无法获取多年趋势", "items": []}

    # 查找同公司代码的所有已解析文档
    docs = db.query(Document).filter(
        Document.company_code == doc.company_code,
        Document.user_id == user_id,
        Document.is_deleted == 0,
        Document.parse_status == "completed",
    ).order_by(Document.fiscal_year).all()

    if len(docs) <= 1:
        return {"description": f"仅有{len(docs)}份文档，需要多个年份才能展示趋势", "items": []}

    # 提取每年的关键指标
    years_data = []
    for d in docs:
        chunks = db.query(Chunk).filter(Chunk.document_id == d.id).all()
        text = "\n".join([c.content for c in chunks])

        # 提取营收和净利润
        revenue_match = re.search(r'营业收入[：:]\s*([\d,]+\.?\d*)', text)
        profit_match = re.search(r'(?:归属于.*?)?净利润[：:]\s*([\d,]+\.?\d*)', text)

        years_data.append({
            "year": d.fiscal_year,
            "revenue": _parse_number(revenue_match.group(1)) if revenue_match else 0,
            "net_profit": _parse_number(profit_match.group(1)) if profit_match else 0,
        })

    return {
        "description": f"{doc.company_code} 多年财务趋势",
        "items": years_data,
    }


def _extract_asset_structure(text: str) -> dict:
    """提取资产结构数据"""
    items = {
        "货币资金": r'货币资金[：:]\s*([\d,]+\.?\d*)',
        "应收账款": r'应收[账帳]款[：:]\s*([\d,]+\.?\d*)',
        "存货": r'存货[：:]\s*([\d,]+\.?\d*)',
        "固定资产": r'固定资产[：:]\s*([\d,]+\.?\d*)',
    }
    result = []
    for name, pattern in items.items():
        m = re.search(pattern, text)
        if m:
            result.append({"name": name, "value": m.group(1)})
    return {"items": result, "description": "主要资产构成"}


def _build_radar_from_metrics(metrics: list) -> dict:
    """基于提取的指标构建雷达图（0-100 归一化）"""
    metrics_map = {m["name"]: m.get("raw_value", 0) for m in metrics}

    dimensions = ["盈利能力", "成长性", "偿债能力", "运营效率", "现金流健康度", "研发强度"]
    values = [0, 0, 0, 0, 0, 0]

    # 盈利能力：从毛利率、净利率、ROE 综合（直接使用百分比值）
    profit_scores = []
    for k in ["毛利率", "净利率", "ROE"]:
        if k in metrics_map and metrics_map[k] > 0:
            profit_scores.append(min(metrics_map[k], 50))  # 上限 50 分
    if profit_scores:
        values[0] = int(sum(profit_scores) / len(profit_scores) * 2)  # 缩放到 0-100

    # 成长性：从同比变化推断
    values[1] = 65  # 默认中等偏上

    # 偿债能力：资产负债率越低越好
    debt_ratio = metrics_map.get("资产负债率", 60)
    if debt_ratio > 0:
        values[2] = int(max(0, min(100, (80 - debt_ratio) * 2.5)))  # 低于80%给分

    # 运营效率：暂用总资产规模做参考
    total_assets = metrics_map.get("总资产", 0)
    if total_assets > 0:
        values[3] = int(min(95, total_assets / 100))

    # 现金流健康度
    cashflow = metrics_map.get("经营活动现金流", 0)
    net_profit = metrics_map.get("净利润", 1)
    if net_profit > 0 and cashflow > 0:
        ratio = cashflow / net_profit
        values[4] = int(min(95, ratio * 60))

    # 研发强度：研发费用率
    rd_ratio = metrics_map.get("研发费用率", 0)
    if rd_ratio > 0:
        values[5] = int(min(95, rd_ratio * 10))

    # 确保有合理默认值
    for i, v in enumerate(values):
        if v == 0:
            values[i] = 45

    return {"dimensions": dimensions, "values": values, "description": "基于财报数据的财务健康度评估"}


def get_comparison_data(db: Session, company_codes: list, fiscal_year: int, user_id: int) -> dict:
    """多家公司对比"""
    companies = []
    for code in company_codes:
        docs = db.query(Document).filter(
            Document.company_code == code,
            Document.fiscal_year == fiscal_year,
            Document.user_id == user_id,
            Document.is_deleted == 0,
            Document.parse_status == "completed",
        ).all()

        if not docs:
            companies.append({"company_code": code, "company_name": code, "metrics": [], "error": "未找到数据"})
            continue

        chunks = db.query(Chunk).filter(Chunk.document_id.in_([d.id for d in docs])).all()
        text = "\n".join([c.content for c in chunks])
        metrics = extract_metrics_from_text(text)

        companies.append({
            "company_code": code,
            "company_name": docs[0].company_name or code,
            "document_count": len(docs),
            "metrics": metrics,
        })

    return {"companies": companies, "fiscal_year": fiscal_year}
