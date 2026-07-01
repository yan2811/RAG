# 基于 RAG 架构的财报智能分析系统 — 系统设计规格书

## 基本信息

- **项目类型**: 毕业设计
- **选题来源**: 中国国际大学生创新大赛（2025）产业赛道 — 中联企业管理集团命题
- **设计日期**: 2026-06-04
- **工作量**: 6 个月（24 周）
- **模块总数**: 9 个（不少于 8 个）

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue3 + Vite + TypeScript + Element Plus (Vue Pure Admin) + Pinia + ECharts |
| 后端 | Python + FastAPI + Uvicorn + Celery |
| 数据库 | MySQL 8.0 + ChromaDB (向量) + Redis (缓存/队列) |
| AI 引擎 | DeepSeek-V4-Pro (生成/改写) + BGE-large-zh-v1.5 (Embedding) + BGE-Reranker-v2-m3 (重排序) |
| RAG 框架 | LangChain + LangGraph + LlamaIndex |
| 文档解析 | PyMuPDF + Camelot-py + PaddleOCR + Unstructured |
| 报告生成 | WeasyPrint / ReportLab |

## 系统架构

```
Vue3 SPA (Element Plus)
    ↓ HTTP REST + SSE
FastAPI 后端 (/api/v1/)
    ↓
RAG 核心编排层 (LangChain + LangGraph)
    ↓
MySQL 8.0 + ChromaDB + Redis + 文件存储
    ↓
DeepSeek-V4-Pro + BGE-Embedding + BGE-Reranker
```

## 9 个功能模块

### M1 · 文档智能解析引擎

- PDF 文件上传 + 校验（格式/大小/哈希去重）
- 类型识别（年报/季报/招股书/审计报告）
- PyMuPDF 文本提取 + Camelot 表格结构化（含合并单元格还原）
- 按财报标准章节切分（管理层讨论/三张表/附注/风险提示）
- PaddleOCR 扫描件兜底（文字覆盖率 < 80% 时触发）
- 结构化存储（文本→ChromaDB，表格+元数据→MySQL）

### M2 · 知识库构建与索引

- 分块策略：文本 800-1200 tokens/chunk，表格独立 chunk，指标实体单独抽取
- BGE-large-zh-v1.5 Embedding → ChromaDB HNSW 向量索引
- BM25 + jieba 分词全文索引
- 混合检索：向量 Top-20 + BM25 Top-20 → RRF 融合 → BGE-Reranker 精排 Top-5
- 来源多样性保证（至少 2 个不同章节）

### M3 · 知识库高级管理

- 文档版本管理（版本上传/切换/diff 对比/回滚）
- 标签分类体系（自定义标签/批量打标/标签筛选）
- 批量导入导出（ZIP 上传/Excel CSV 导出）
- 知识库概览统计（文档数/公司数/年度分布/索引状态/存储用量）
- 软删除 + 回收站机制（30 天可恢复）

### M4 · 智能问答引擎（核心）

- 6 步全链路：查询改写 → 混合检索 → Rerank 精排 → 上下文组装 → LLM 流式生成 → 后处理
- 查询改写：HyDE 策略 + 问题分类路由
- SSE 流式输出（type: thinking / sources / answer / done）
- 支持 6 类问答：指标查询/趋势分析/同比对比/跨公司对比/风险识别/合规检查
- 后处理：引用来源注入/金额格式化/敏感词过滤

### M5 · 多步推理 Agent

- LangGraph StateGraph 编排
- 流程：问题分解 → 并行检索 → 指标抽取 → 交叉验证 → 综合生成
- Agent 可调用工具：retrieve / query_metric / calculate_ratio / compare_companies

### M6 · 财报分析仪表盘

- 图表类型：趋势折线图/结构饼图/瀑布图/雷达图/对比柱状图/杜邦分析树
- ECharts 交互式渲染（年份切换/指标筛选/图表联动/钻取）
- Pandas + NumPy 指标计算
- 布局：核心指标卡片 + 左右并排图表 + 全宽杜邦分析树

### M7 · AI 报告生成

- 报告类型：单公司年报/季报/多公司对比/自定义
- 8 段式结构：指标速览→收入→成本费用→资产负债→现金流→风险→同业对标→总结
- 指标精确查询走 MySQL（不走 LLM），分析文字由 DeepSeek 生成
- Markdown 在线预览 + PDF 下载

### M8 · 对话管理

- 会话 CRUD + 多轮对话上下文（最近 5 轮）
- 消息气泡渲染（Markdown + 代码高亮 + 来源标注）
- 滚动加载历史消息
- 对话导出为 Markdown
- 问答反馈（点赞/点踩 + 原因）

### M9 · 系统管理

- 用户注册/登录（JWT + bcrypt）
- RBAC 权限（超级管理员/管理员/普通用户/访客，菜单+按钮+数据权限）
- 操作日志审计
- 系统配置（API Key/模型选择/chunk 参数/Logo）
- 数据统计仪表盘

## 数据库设计（13 张表）

users, documents, chunks, financial_metrics, sessions, messages, reports, document_versions, tags, document_tags, roles, user_roles, operation_logs, system_settings, feedbacks

## 前端页面结构

```
/login                      → 登录/注册
/dashboard                  → 首页工作台
/documents                  → 文档列表
/documents/upload           → 上传文档
/documents/:id              → 文档详情
/knowledge                  → 知识库概览
/knowledge/index            → 索引管理
/knowledge/tags             → 标签管理
/knowledge/versions/:docId  → 版本历史
/chat                       → 对话（默认最近会话）
/chat/:sessionId            → 具体会话
/reports                    → 报告列表
/reports/generate           → 生成报告
/reports/:id                → 报告预览
/analytics/:docId           → 分析仪表盘
/analytics/compare          → 跨公司对比
/admin/users                → 用户管理
/admin/roles                → 角色管理
/admin/logs                 → 操作日志
/admin/settings             → 系统配置
/admin/stats                → 系统统计
```

## 6 个月实施计划

| 阶段 | 时间 | 内容 | 产出 |
|------|------|------|------|
| P0 | 第 1-3 周 | 项目脚手架搭建、M9 用户认证+RBAC、前后端打通 | 登录注册可用 |
| P1 | 第 4-7 周 | M1 文档解析引擎、文档管理前端页面 | PDF→结构化数据全流程 |
| P2 | 第 8-11 周 | M2 向量索引+混合检索、M3 知识库管理 | 知识库构建+管理完成 |
| P3 | 第 12-15 周 | M4 智能问答引擎、M8 对话管理 | 核心问答端到端跑通 |
| P4 | 第 16-19 周 | M5 Agent 多步推理、M6 仪表盘、M7 报告生成 | 全功能开发完成 |
| P5 | 第 20-22 周 | 全系统联调、Bug 修复、性能优化、UI 打磨 | 系统稳定可用 |
| P6 | 第 23-24 周 | 论文撰写、答辩 PPT、演示演练 | 交付 |

## 关键设计原则

- 财务指标精确查询走 MySQL，不允许 LLM 直接报数（防幻觉）
- DeepSeek API Key 通过环境变量注入
- SSE 流式响应用于问答接口
- 前端路由守卫 + 后端中间件双重权限校验
- 所有金额标注币种和单位，百分比保留两位小数
