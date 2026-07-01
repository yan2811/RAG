"""
大语言模型服务（M4 模块）
DeepSeek-V4-Pro API 调用
- 兼容 OpenAI 协议 (base_url 不含 anthropic)
- 兼容 Anthropic 协议 (base_url 含 anthropic)
支持流式生成、查询改写、System Prompt 管理
"""
import logging
from typing import Optional, Generator, List, Dict
from app.core.config import settings

logger = logging.getLogger(__name__)

# 判断使用哪种协议
_USE_ANTHROPIC = "anthropic" in settings.DEEPSEEK_BASE_URL.lower()

# 全局客户端（懒初始化）
_openai_client = None
_anthropic_client = None


def _get_openai_client():
    """获取 OpenAI 兼容客户端"""
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        if not settings.DEEPSEEK_API_KEY or settings.DEEPSEEK_API_KEY.startswith("sk-your"):
            return None
        _openai_client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        logger.info(f"OpenAI 兼容客户端初始化: {settings.DEEPSEEK_BASE_URL}")
    return _openai_client


def _get_anthropic_client():
    """获取 Anthropic 兼容客户端"""
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        if not settings.DEEPSEEK_API_KEY or settings.DEEPSEEK_API_KEY.startswith("sk-your"):
            return None
        _anthropic_client = anthropic.Anthropic(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        logger.info(f"Anthropic 兼容客户端初始化: {settings.DEEPSEEK_BASE_URL}")
    return _anthropic_client


# ===== System Prompt =====

SYSTEM_PROMPT = """你是一个专业的财务分析AI助手，名为"财报RAG助手"。你不仅能查找数据，还能基于已有数据进行智能计算和推导。

## 核心规则
1. **优先检索、智能计算**：从检索内容中提取相关数据。如果用户问的指标(如毛利率)没有直接给出，但检索内容中有营业收入和营业成本，你必须自己计算：毛利率=(营收-成本)/营收×100%。同理适用净利率、ROE、增长率等。
2. **主动推导**：
   - 有营收和成本 → 可算毛利率
   - 有营收和净利润 → 可算净利率
   - 有净利润和净资产 → 可算ROE
   - 有今昔两年数据 → 可算同比增长率
   - 有各部分金额和总额 → 可算占比
3. **数据溯源**：检索到的数据和计算出的结果都标注来源，计算过程也说明。
4. **诚实地说明**：检索内容中有直接数据就说"财报显示"；自己计算的就说明"根据财报数据计算得出"；都没有才说"数据不足"。
5. **格式规范**：金额用"亿元"；百分比保留2位小数；对比用表格。

## 输出格式
1. 直接给答案（数字+单位）
2. 说明是直接引用还是计算得出
3. 补充来源和分析

当前日期：{current_date}
"""

FINANCIAL_ANALYSIS_PROMPT = """你是一个资深财务分析师，请基于以下财报数据进行专业分析。

分析要点：
1. 关键财务指标的变化趋势及原因
2. 与行业平均水平的的对比（如数据可用）
3. 潜在风险提示
4. 总结与展望

请用专业但易于理解的语言撰写分析，每个观点都要有数据支撑。
"""


def get_system_prompt(current_date: str = "2026-06-04") -> str:
    """获取格式化的 System Prompt"""
    return SYSTEM_PROMPT.format(current_date=current_date)


# ===== 查询改写 =====

def rewrite_query(original_query: str) -> str:
    """
    智能查询改写：识别财务指标并扩展相关检索词
    例如"毛利率多少" → "毛利率 营业收入 营业成本"
    """
    # 财务指标→原始数据映射
    FINANCE_TERM_EXPAND = {
        "毛利率": "营业收入 营业成本 毛利 毛利率",
        "净利率": "营业收入 净利润 净利率",
        "ROE": "净利润 净资产 净资产收益率 ROE",
        "ROA": "净利润 总资产 总资产收益率 ROA",
        "增长率": "同比增长 增长率 营业收入 净利润",
        "资产负债率": "总资产 总负债 资产负债率",
        "每股收益": "基本每股收益 稀释每股收益 EPS",
        "研发费用率": "研发费用 营业收入 研发费用率",
    }

    expanded = original_query
    for term, expansion in FINANCE_TERM_EXPAND.items():
        if term in original_query:
            expanded = f"{original_query} {expansion}"
            break

    if _USE_ANTHROPIC:
        client = _get_anthropic_client()
        if client is None:
            return original_query
        try:
            response = client.messages.create(
                model="deepseek-chat",
                max_tokens=200,
                system="你是一个查询优化助手。将用户的口语化财务问题改写为精确的检索查询。提取关键实体（公司名、年份、指标名），去除冗余表达。只输出改写后的查询，不要解释。",
                messages=[{"role": "user", "content": f"原始问题：{original_query}\n改写后的检索查询："}],
            )
            rewritten = response.content[0].text.strip()
            logger.info(f"查询改写: '{original_query}' → '{rewritten}'")
            return rewritten if rewritten else original_query
        except Exception as e:
            logger.warning(f"查询改写失败(Anthropic): {e}")
            return original_query
    else:
        client = _get_openai_client()
        if client is None:
            return original_query
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个查询优化助手。将用户的口语化财务问题改写为精确的检索查询。提取关键实体（公司名、年份、指标名），去除冗余表达。只输出改写后的查询，不要解释。"},
                    {"role": "user", "content": f"原始问题：{original_query}\n改写后的检索查询："},
                ],
                temperature=0.1,
                max_tokens=200,
            )
            rewritten = response.choices[0].message.content.strip()
            logger.info(f"查询改写: '{original_query}' → '{rewritten}'")
            return rewritten if rewritten else original_query
        except Exception as e:
            logger.warning(f"查询改写失败(OpenAI): {e}")
            return original_query


# ===== LLM 流式生成 =====

def stream_generate(
    messages: List[Dict[str, str]],
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> Generator[str, None, None]:
    """
    流式调用 DeepSeek API 生成回答
    自动适配 OpenAI/Anthropic 协议
    """
    if _USE_ANTHROPIC:
        yield from _stream_anthropic(messages, temperature, max_tokens)
    else:
        yield from _stream_openai(messages, temperature, max_tokens)


def _stream_openai(messages, temperature, max_tokens):
    """OpenAI 协议流式生成"""
    client = _get_openai_client()
    if client is None:
        yield "错误：DeepSeek API Key 未配置。请在系统设置中填入 API Key。"
        return
    try:
        stream = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"OpenAI 流式生成失败: {e}")
        yield f"\n\n生成过程中出现错误：{str(e)}"


def _stream_anthropic(messages, temperature, max_tokens):
    """Anthropic 协议流式生成"""
    client = _get_anthropic_client()
    if client is None:
        yield "错误：DeepSeek API Key 未配置。请在系统设置中填入 API Key。"
        return

    # Anthropic: system 是独立参数，messages 只有 user/assistant
    system_content = ""
    anthropic_messages = []
    for m in messages:
        if m["role"] == "system":
            system_content = m["content"]
        else:
            anthropic_messages.append({"role": m["role"], "content": m["content"]})

    try:
        with client.messages.stream(
            model="deepseek-chat",
            max_tokens=max_tokens,
            system=system_content if system_content else None,
            messages=anthropic_messages,
            temperature=temperature,
        ) as stream:
            for text in stream.text_stream:
                yield text
    except Exception as e:
        logger.error(f"Anthropic 流式生成失败: {e}")
        yield f"\n\n生成过程中出现错误：{str(e)}"


def generate_sync(
    messages: List[Dict[str, str]],
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """非流式调用（用于报告生成、查询改写等场景）"""
    if _USE_ANTHROPIC:
        client = _get_anthropic_client()
        if client is None:
            return ""
        system_content = ""
        anthropic_messages = []
        for m in messages:
            if m["role"] == "system":
                system_content = m["content"]
            else:
                anthropic_messages.append({"role": m["role"], "content": m["content"]})
        try:
            response = client.messages.create(
                model="deepseek-chat",
                max_tokens=max_tokens,
                system=system_content if system_content else None,
                messages=anthropic_messages,
                temperature=temperature,
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic 同步生成失败: {e}")
            return ""
    else:
        client = _get_openai_client()
        if client is None:
            return ""
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI 同步生成失败: {e}")
            return ""


# ===== 答案后处理 =====

def post_process_answer(answer: str, sources: List[dict]) -> str:
    """对 LLM 生成的答案进行后处理：确保有来源标注、格式化金额单位"""
    if sources and "来源" not in answer and "source" not in answer.lower():
        source_texts = []
        for s in sources[:3]:
            section = s.get("section", s.get("metadata", {}).get("section_title", "未知章节"))
            page = s.get("page", s.get("metadata", {}).get("page_start", "?"))
            source_texts.append(f"- {section}（第{page}页）")
        if source_texts:
            answer += f"\n\n---\n**数据来源：**\n" + "\n".join(source_texts)
    return answer


def analyze_question_type(query: str) -> str:
    """分析问题类型：metric_query / trend_analysis / comparison / risk_check / general"""
    metric_keywords = ["多少", "是多少", "金额", "数值", "数据", "指标"]
    trend_keywords = ["趋势", "变化", "增长", "下降", "逐年", "近几", "走势", "同比", "环比"]
    compare_keywords = ["对比", "比较", "vs", "哪个更", "差距"]
    risk_keywords = ["风险", "隐患", "问题", "异常", "亏损"]

    if any(kw in query for kw in metric_keywords):
        return "metric_query"
    if any(kw in query for kw in trend_keywords):
        return "trend_analysis"
    if any(kw in query for kw in compare_keywords):
        return "comparison"
    if any(kw in query for kw in risk_keywords):
        return "risk_check"
    return "general"
