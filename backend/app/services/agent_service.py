"""
多步推理 Agent 服务（M5 模块）
对复杂财务问题自动拆解为子任务，逐步检索分析后综合回答
"""
import logging
from typing import List, Dict
from sqlalchemy.orm import Session
from app.services.llm_service import generate_sync, FINANCIAL_ANALYSIS_PROMPT
from app.services.search_service import hybrid_search
from app.models.document import Document, Chunk

logger = logging.getLogger(__name__)

# 问题拆解 Prompt
DECOMPOSE_PROMPT = """你是一个财务分析专家。请将以下复杂问题拆解为 3-5 个具体的子问题，每个子问题应针对具体的财务指标或分析维度。

规则：
1. 每个子问题应能够通过检索财报内容独立回答
2. 子问题应覆盖：指标数据、变化趋势、驱动因素、风险提示等维度
3. 用数字序号列出，每行一个子问题
4. 只输出子问题，不要解释

原始问题：{question}

拆解后的子问题："""


def decompose_question(question: str) -> List[str]:
    """
    使用 LLM 将复杂问题拆解为子问题列表
    :param question: 用户提出的复杂分析问题
    :return: 子问题列表
    """
    prompt = DECOMPOSE_PROMPT.format(question=question)
    result = generate_sync(
        messages=[
            {"role": "system", "content": "你是一个财务分析专家，擅长拆解复杂分析问题。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=500,
    )

    if not result:
        return [question]  # 拆解失败，返回原问题

    # 解析子问题列表
    sub_questions = []
    for line in result.strip().split("\n"):
        line = line.strip()
        # 匹配 "1. xxx" 或 "1) xxx" 或 "- xxx" 格式
        if line and any(line.startswith(c) for c in ["1", "2", "3", "4", "5", "-", "*"]):
            # 去掉编号前缀
            for i in range(9):
                for sep in [". ", ") ", ".", ")", "、"]:
                    if line.startswith(f"{i}{sep}"):
                        line = line[len(f"{i}{sep}"):].strip()
            sub_questions.append(line)

    if not sub_questions:
        sub_questions.append(question)

    logger.info(f"问题拆解: {len(sub_questions)} 个子问题")
    return sub_questions


def execute_agent_reasoning(
    db: Session,
    question: str,
    document_ids: List[int] = None,
) -> Dict:
    """
    执行多步推理 Agent 流程：
    1. 问题拆解 → 2. 并行检索每个子问题 → 3. 提取指标 → 4. 综合生成报告

    :param db: 数据库会话
    :param question: 用户原始问题
    :param document_ids: 限定的文档 ID 范围
    :return: {sub_questions, search_results, final_report}
    """
    # Step 1: 拆解问题
    sub_questions = decompose_question(question)

    # Step 2: 对每个子问题执行检索
    all_results = []
    for i, sq in enumerate(sub_questions):
        search_results = hybrid_search(
            query=sq,
            top_k=3,
            filter_doc_ids=document_ids,
        )
        result_texts = []
        for r in search_results:
            meta = r.get("metadata", {})
            result_texts.append({
                "text": r["text"][:500],
                "section": meta.get("section_title", ""),
                "page": meta.get("page_start", ""),
            })
        all_results.append({
            "sub_question": sq,
            "index": i + 1,
            "results": result_texts,
        })

    # Step 3: 基于检索结果综合生成分析报告
    context_for_synthesis = ""
    for ar in all_results:
        context_for_synthesis += f"\n## 子问题{ar['index']}：{ar['sub_question']}\n"
        for r in ar["results"]:
            context_for_synthesis += f"- [{r['section']} P{r['page']}] {r['text'][:300]}\n"

    # Step 4: 综合生成
    synthesis_prompt = FINANCIAL_ANALYSIS_PROMPT + f"\n\n## 检索到的财报数据\n{context_for_synthesis}\n\n## 原始问题\n{question}\n\n请基于以上数据进行综合分析。"

    final_report = generate_sync(
        messages=[
            {"role": "system", "content": synthesis_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.2,
        max_tokens=3000,
    )

    return {
        "original_question": question,
        "sub_questions": [{"index": i + 1, "question": q} for i, q in enumerate(sub_questions)],
        "search_results": all_results,
        "final_report": final_report or "分析报告生成失败，请确认已配置 API Key。",
    }
